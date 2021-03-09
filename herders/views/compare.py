import copy
import itertools
from operator import attrgetter

from django.utils.text import slugify
from django.http import HttpResponseBadRequest
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from bestiary.models import Rune, RuneCraft, Artifact, ArtifactCraft

from herders.decorators import username_case_redirect
from herders.models import RuneInstance, RuneCraftInstance, ArtifactInstance, ArtifactCraftInstance, Summoner


def _find_comparison_winner(data):
    for key, val in data.items():
        if isinstance(val, dict) and "summoner" not in val.keys():
            _find_comparison_winner(val)
        else:
            record = data[key]
            if record["summoner"] > record["follower"]:
                record["winner"] = "summoner" 
            elif record["summoner"] < record["follower"]:
                record["winner"] = "follower"
            else:
                record["winner"] = "tie"


@username_case_redirect
@login_required
def summary(request, profile_name, follow_username):
    try:
        summoner = Summoner.objects.select_related('user').get(user__username=profile_name)
    except Summoner.DoesNotExist:
        return HttpResponseBadRequest()
    try:
        follower = Summoner.objects.select_related('user').get(user__username=follow_username)
    except Summoner.DoesNotExist:
        return HttpResponseBadRequest()

    is_owner = (request.user.is_authenticated and summoner.user == request.user)

    if not is_owner:
        return render(request, 'herders/profile/not_public.html', {})

    can_compare = (follower in summoner.following.all() and follower in summoner.followed_by.all() and follower.public)

    context = {
        'is_owner': is_owner,
        'can_compare': can_compare,
        'profile_name': profile_name,
        'follower_name': follow_username,
        'comparison': {},
        'view': 'compare-summary',
    }

    return render(request, 'herders/profile/compare/summary.html', context)


def _compare_runes(summoner, follower):
    stats = {stat[1]: {"summoner": 0, "follower": 0} for stat in sorted(Rune.STAT_CHOICES, key=lambda x: x[1])}
    qualities = {quality[1]: {"summoner": 0, "follower": 0} for quality in Rune.QUALITY_CHOICES}
    qualities[None] = {"summoner": 0, "follower": 0}
    report_runes = {
        'count': {"summoner": 0, "follower": 0},
        'stars': {
            6: {"summoner": 0, "follower": 0},
            5: {"summoner": 0, "follower": 0},
            4: {"summoner": 0, "follower": 0},
            3: {"summoner": 0, "follower": 0},
            2: {"summoner": 0, "follower": 0},
            1: {"summoner": 0, "follower": 0},
        },
        'sets': {rune_set[1]: {"summoner": 0, "follower": 0} for rune_set in sorted(Rune.TYPE_CHOICES, key=lambda x: x[1])},
        'quality': copy.deepcopy(qualities),
        'quality_original': copy.deepcopy(qualities),
        'slot': {
            1: {"summoner": 0, "follower": 0},
            2: {"summoner": 0, "follower": 0},
            3: {"summoner": 0, "follower": 0},
            4: {"summoner": 0, "follower": 0},
            5: {"summoner": 0, "follower": 0},
            6: {"summoner": 0, "follower": 0},
        },
        'main_stat': copy.deepcopy(stats),
        'innate_stat': copy.deepcopy(stats),
        'substats': copy.deepcopy(stats),
        'worth': {"summoner": 0, "follower": 0},
    }
    report_runes['innate_stat'][None] = {"summoner": 0, "follower": 0}
    owners = [summoner, follower]
    runes = RuneInstance.objects.select_related('owner').filter(owner__in=owners).order_by('owner')

    rune_substats = dict(Rune.STAT_CHOICES)

    for owner, iter_ in itertools.groupby(runes, key=attrgetter('owner')):
        owner_str = "summoner"
        if owner == follower:
            owner_str = "follower"
        runes_owner = list(iter_)
        report_runes['count'][owner_str] = len(runes_owner)
        for rune in runes_owner:
            for sub_stat in rune.substats:
                report_runes['substats'][rune_substats[sub_stat]][owner_str] += 1

            report_runes['stars'][rune.stars][owner_str] += 1
            report_runes['sets'][rune.get_type_display()][owner_str] += 1
            report_runes['quality'][rune.get_quality_display()][owner_str] += 1
            report_runes['quality_original'][rune.get_original_quality_display()][owner_str] += 1
            report_runes['slot'][rune.slot][owner_str] += 1
            report_runes['main_stat'][rune.get_main_stat_display()][owner_str] += 1
            report_runes['innate_stat'][rune.get_innate_stat_display()][owner_str] += 1
            report_runes['worth'][owner_str] += rune.value

    _find_comparison_winner(report_runes)

    return report_runes


@username_case_redirect
@login_required
def runes(request, profile_name, follow_username):
    try:
        summoner = Summoner.objects.select_related('user').get(user__username=profile_name)
    except Summoner.DoesNotExist:
        return HttpResponseBadRequest()
    try:
        follower = Summoner.objects.select_related('user').get(user__username=follow_username)
    except Summoner.DoesNotExist:
        return HttpResponseBadRequest()

    is_owner = (request.user.is_authenticated and summoner.user == request.user)

    if not is_owner:
        return render(request, 'herders/profile/not_public.html', {})

    can_compare = (follower in summoner.following.all() and follower in summoner.followed_by.all() and follower.public)

    context = {
        'is_owner': is_owner,
        'can_compare': can_compare,
        'profile_name': profile_name,
        'follower_name': follow_username,
        'runes': _compare_runes(summoner, follower),
        'view': 'compare-runes',
        'subviews': {type_[1]: slugify(type_[1]) for type_ in RuneCraft.CRAFT_CHOICES}
    }

    return render(request, 'herders/profile/compare/runes/base.html', context)


def _compare_rune_crafts(summoner, follower, craft_type):
    stats = {stat[1]: {"summoner": 0, "follower": 0} for stat in sorted(RuneCraft.STAT_CHOICES, key=lambda x: x[1])}
    sets = {rune_set[1]: {"summoner": 0, "follower": 0} for rune_set in sorted(RuneCraft.TYPE_CHOICES, key=lambda x: x[1])}
    sets[None] = {"summoner": 0, "follower": 0}
    qualities = {quality[1]: {"summoner": 0, "follower": 0} for quality in RuneCraft.QUALITY_CHOICES}
    report = {
        'count': {"summoner": 0, "follower": 0},
        'sets': copy.deepcopy(sets),
        'quality': copy.deepcopy(qualities),
        'stat': copy.deepcopy(stats),
        'worth': {"summoner": 0, "follower": 0},
    }
    owners = [summoner, follower]
    runes = RuneCraftInstance.objects.select_related('owner').filter(owner__in=owners, type=craft_type).order_by('owner')

    for owner, iter_ in itertools.groupby(runes, key=attrgetter('owner')):
        owner_str = "summoner"
        if owner == follower:
            owner_str = "follower"
        records_owner = list(iter_)
        for record in records_owner:
            report['count'][owner_str] += record.quantity
            report['sets'][record.get_rune_display()][owner_str] += record.quantity
            report['quality'][record.get_quality_display()][owner_str] += record.quantity
            report['stat'][record.get_stat_display()][owner_str] += record.quantity
            report['worth'][owner_str] += record.value * record.quantity

    _find_comparison_winner(report)

    return report


@username_case_redirect
@login_required
def rune_crafts(request, profile_name, follow_username, rune_craft_slug):
    try:
        summoner = Summoner.objects.select_related('user').get(user__username=profile_name)
    except Summoner.DoesNotExist:
        return HttpResponseBadRequest()
    try:
        follower = Summoner.objects.select_related('user').get(user__username=follow_username)
    except Summoner.DoesNotExist:
        return HttpResponseBadRequest()

    is_owner = (request.user.is_authenticated and summoner.user == request.user)

    if not is_owner:
        return render(request, 'herders/profile/not_public.html', {})

    can_compare = (follower in summoner.following.all() and follower in summoner.followed_by.all() and follower.public)

    craft_types = {slugify(type_[1]): {"idx": type_[0], "name": type_[1]} for type_ in RuneCraft.CRAFT_CHOICES}
    craft_type = craft_types.get(rune_craft_slug, None)
    if craft_type is None:
        return HttpResponseBadRequest()

    context = {
        'is_owner': is_owner,
        'can_compare': can_compare,
        'profile_name': profile_name,
        'follower_name': follow_username,
        'crafts': _compare_rune_crafts(summoner, follower, craft_type["idx"]),
        'view': 'compare-runes',
        'craft_type': craft_type["name"],
        'subviews': {type_[1]: slugify(type_[1]) for type_ in RuneCraft.CRAFT_CHOICES}
    }

    return render(request, 'herders/profile/compare/runes/crafts.html', context)


def _compare_artifacts(summoner, follower):
    qualities = {quality[1]: {"summoner": 0, "follower": 0} for quality in Artifact.QUALITY_CHOICES}
    report = {
        'count': {"summoner": 0, "follower": 0},
        'quality': copy.deepcopy(qualities),
        'quality_original': copy.deepcopy(qualities),
        'slot': {artifact_slot[1]: {"summoner": 0, "follower": 0} for artifact_slot in (Artifact.ARCHETYPE_CHOICES + Artifact.NORMAL_ELEMENT_CHOICES)},
        'main_stat': {stat[1]: {"summoner": 0, "follower": 0} for stat in sorted(Artifact.MAIN_STAT_CHOICES, key=lambda x: x[1])},
        'substats': {effect[1]: {"summoner": 0, "follower": 0} for effect in sorted(Artifact.EFFECT_CHOICES, key=lambda x: x[1])},
    }
    owners = [summoner, follower]
    artifacts = ArtifactInstance.objects.select_related('owner').filter(owner__in=owners).order_by('owner')

    artifact_substats = dict(Artifact.EFFECT_CHOICES)

    for owner, iter_ in itertools.groupby(artifacts, key=attrgetter('owner')):
        owner_str = "summoner"
        if owner == follower:
            owner_str = "follower"
        artifacts_owner = list(iter_)
        report['count'][owner_str] = len(artifacts_owner)
        for artifact in artifacts_owner:
            for sub_stat in artifact.effects:
                report['substats'][artifact_substats[sub_stat]][owner_str] += 1

            report['quality'][artifact.get_quality_display()][owner_str] += 1
            report['quality_original'][artifact.get_original_quality_display()][owner_str] += 1
            report['slot'][artifact.get_precise_slot_display()][owner_str] += 1
            report['main_stat'][artifact.get_main_stat_display()][owner_str] += 1

    _find_comparison_winner(report)

    return report


@username_case_redirect
@login_required
def artifacts(request, profile_name, follow_username):
    try:
        summoner = Summoner.objects.select_related('user').get(user__username=profile_name)
    except Summoner.DoesNotExist:
        return HttpResponseBadRequest()
    try:
        follower = Summoner.objects.select_related('user').get(user__username=follow_username)
    except Summoner.DoesNotExist:
        return HttpResponseBadRequest()

    is_owner = (request.user.is_authenticated and summoner.user == request.user)

    if not is_owner:
        return render(request, 'herders/profile/not_public.html', {})

    can_compare = (follower in summoner.following.all() and follower in summoner.followed_by.all() and follower.public)

    context = {
        'is_owner': is_owner,
        'can_compare': can_compare,
        'profile_name': profile_name,
        'follower_name': follow_username,
        'artifacts': _compare_artifacts(summoner, follower),
        'view': 'compare-artifacts',
    }

    return render(request, 'herders/profile/compare/artifacts/base.html', context)


def _compare_artifact_crafts(summoner, follower):
    report = {
        'count': {"summoner": 0, "follower": 0},
        'quality': {quality[1]: {"summoner": 0, "follower": 0} for quality in Artifact.QUALITY_CHOICES},
        'slot': {artifact_slot[1]: {"summoner": 0, "follower": 0} for artifact_slot in (Artifact.ARCHETYPE_CHOICES + Artifact.NORMAL_ELEMENT_CHOICES)},
        'substats': {effect[1]: {"summoner": 0, "follower": 0} for effect in sorted(Artifact.EFFECT_CHOICES, key=lambda x: x[1])},
    }
    owners = [summoner, follower]
    artifacts = ArtifactCraftInstance.objects.select_related('owner').filter(owner__in=owners).order_by('owner')

    for owner, iter_ in itertools.groupby(artifacts, key=attrgetter('owner')):
        owner_str = "summoner"
        if owner == follower:
            owner_str = "follower"
        artifacts_owner = list(iter_)
        for artifact in artifacts_owner:
            report['substats'][artifact.get_effect_display()][owner_str] += artifact.quantity
            report['quality'][artifact.get_quality_display()][owner_str] += artifact.quantity
            report['slot'][artifact.get_archetype_display() or artifact.get_element_display()][owner_str] += artifact.quantity
            report['count'][owner_str] += artifact.quantity

    _find_comparison_winner(report)

    return report


@username_case_redirect
@login_required
def artifact_crafts(request, profile_name, follow_username):
    try:
        summoner = Summoner.objects.select_related('user').get(user__username=profile_name)
    except Summoner.DoesNotExist:
        return HttpResponseBadRequest()
    try:
        follower = Summoner.objects.select_related('user').get(user__username=follow_username)
    except Summoner.DoesNotExist:
        return HttpResponseBadRequest()

    is_owner = (request.user.is_authenticated and summoner.user == request.user)

    if not is_owner:
        return render(request, 'herders/profile/not_public.html', {})

    can_compare = (follower in summoner.following.all() and follower in summoner.followed_by.all() and follower.public)

    context = {
        'is_owner': is_owner,
        'can_compare': can_compare,
        'profile_name': profile_name,
        'follower_name': follow_username,
        'artifact_craft': _compare_artifact_crafts(summoner, follower),
        'view': 'compare-artifacts',
    }

    return render(request, 'herders/profile/compare/artifacts/crafts.html', context)

from collections import OrderedDict

from django.http import Http404, HttpResponseForbidden
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db import IntegrityError
from django.db.models import Q
from django.forms.formsets import formset_factory
from django.shortcuts import render, redirect, get_object_or_404

from .forms import RegisterUserForm, AddMonsterInstanceForm, EditMonsterInstanceForm, AwakenMonsterInstanceForm, \
    PowerUpMonsterInstanceForm, EditEssenceStorageForm, EditSummonerForm, EditUserForm, EditTeamForm, AddTeamGroupForm, \
    DeleteTeamGroupForm
from .models import Monster, Summoner, MonsterInstance, Fusion, TeamGroup, Team
from .fusion import essences_missing


def register(request):
    form = RegisterUserForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            try:
                # Create the user
                new_user = User.objects.create_user(
                    username=form.cleaned_data['username'],
                    password=form.cleaned_data['password'],
                    email=form.cleaned_data['email'],
                )
                new_user.save()

                new_summoner = Summoner.objects.create(
                    user=new_user,
                    summoner_name=form.cleaned_data['summoner_name'],
                    public=form.cleaned_data['is_public'],
                )
                new_summoner.save()

                # Automatically log them in
                user = authenticate(username=form.cleaned_data['username'], password=form.cleaned_data['password'])
                if user is not None:
                    if user.is_active:
                        login(request, user)
                        return redirect('herders:profile', profile_name=user.username, view_mode='list')
            except IntegrityError:
                form.add_error('username', 'Username already taken')

    context = {'form': form}

    return render(request, 'herders/register.html', context)


def profile(request, profile_name=None, view_mode='list', sort_method='grade'):
    if profile_name is None:
        if request.user.is_authenticated():
            profile_name = request.user.username
        else:
            raise Http404('No user profile specified and not logged in. ')

    summoner = get_object_or_404(Summoner, user__username=profile_name)

    # Determine if the person logged in is the one requesting the view
    is_owner = (request.user.is_authenticated() and summoner.user == request.user) or request.user.is_superuser
    context = {
        'add_monster_form': AddMonsterInstanceForm(),
        'profile_name': profile_name,
        'is_owner': is_owner,
        'view_mode': view_mode,
        'sort_method': sort_method,
        'return_path': request.path,
        'view': 'profile',
    }

    if is_owner or summoner.public:
        if view_mode.lower() == 'list':
            context['monster_stable'] = MonsterInstance.objects.select_related('monster').filter(owner=summoner)
            return render(request, 'herders/profile/profile_view.html', context)
        elif view_mode.lower() == 'box':
            if sort_method == 'grade':
                monster_stable = OrderedDict()
                monster_stable['6*'] = MonsterInstance.objects.select_related('monster').filter(owner=summoner, stars=6).order_by('-level', 'monster__name')
                monster_stable['5*'] = MonsterInstance.objects.select_related('monster').filter(owner=summoner, stars=5).order_by('-level', 'monster__name')
                monster_stable['4*'] = MonsterInstance.objects.select_related('monster').filter(owner=summoner, stars=4).order_by('-level', 'monster__name')
                monster_stable['3*'] = MonsterInstance.objects.select_related('monster').filter(owner=summoner, stars=3).order_by('-level', 'monster__name')
                monster_stable['2*'] = MonsterInstance.objects.select_related('monster').filter(owner=summoner, stars=2).order_by('-level', 'monster__name')
                monster_stable['1*'] = MonsterInstance.objects.select_related('monster').filter(owner=summoner, stars=1).order_by('-level', 'monster__name')
            elif sort_method == 'level':
                monster_stable = OrderedDict()
                monster_stable['40-31'] = MonsterInstance.objects.select_related('monster').filter(owner=summoner, level__gt=30).order_by('-level', '-stars', 'monster__name')
                monster_stable['30-21'] = MonsterInstance.objects.select_related('monster').filter(owner=summoner, level__gt=20).filter(level__lte=30).order_by('-level', '-stars', 'monster__name')
                monster_stable['20-11'] = MonsterInstance.objects.select_related('monster').filter(owner=summoner, level__gt=10).filter(level__lte=20).order_by('-level', '-stars', 'monster__name')
                monster_stable['10-1'] = MonsterInstance.objects.select_related('monster').filter(owner=summoner, level__lte=10).order_by('-level', '-stars', 'monster__name')
            elif sort_method == 'attribute':
                monster_stable = OrderedDict()
                monster_stable['water'] = MonsterInstance.objects.select_related('monster').filter(owner=summoner, monster__element=Monster.ELEMENT_WATER).order_by('-stars', '-level', 'monster__name')
                monster_stable['fire'] = MonsterInstance.objects.select_related('monster').filter(owner=summoner, monster__element=Monster.ELEMENT_FIRE).order_by('-stars', '-level', 'monster__name')
                monster_stable['wind'] = MonsterInstance.objects.select_related('monster').filter(owner=summoner, monster__element=Monster.ELEMENT_WIND).order_by('-stars', '-level', 'monster__name')
                monster_stable['light'] = MonsterInstance.objects.select_related('monster').filter(owner=summoner, monster__element=Monster.ELEMENT_LIGHT).order_by('-stars', '-level', 'monster__name')
                monster_stable['dark'] = MonsterInstance.objects.select_related('monster').filter(owner=summoner, monster__element=Monster.ELEMENT_DARK).order_by('-stars', '-level', 'monster__name')
            else:
                raise Http404('Invalid sort method')

            context['monster_stable'] = monster_stable
            return render(request, 'herders/profile/profile_box.html', context)
        else:
            raise Http404('Unknown profile view mode')
    else:
        return render(request, 'herders/profile/not_public.html')


@login_required
def profile_edit(request, profile_name):
    return_path = request.GET.get(
        'next',
        reverse('herders:profile', kwargs={'profile_name': profile_name, 'view_mode': 'list'})
    )

    is_owner = request.user.username == profile_name or request.user.is_superuser

    user_form = EditUserForm(request.POST or None, instance=request.user)
    summoner_form = EditSummonerForm(request.POST or None, instance=request.user.summoner)

    context = {
        'is_owner': is_owner,
        'profile_name': profile_name,
        'return_path': return_path,
        'user_form': user_form,
        'summoner_form': summoner_form,
    }

    if is_owner:
        if request.method == 'POST' and summoner_form.is_valid() and user_form.is_valid():
            summoner_form.save()
            user_form.save()

            messages.success(request, 'Your profile has been updated.')
            return redirect(return_path)
        else:
            return render(request, 'herders/profile/profile_edit.html', context)
    else:
        return HttpResponseForbidden()


@login_required
def profile_storage(request, profile_name):
    return_path = request.GET.get(
        'next',
        reverse('herders:profile', kwargs={'profile_name': profile_name, 'view_mode': 'list'})
    )
    form = EditEssenceStorageForm(request.POST or None, instance=request.user.summoner)
    form.helper.form_action = request.path + '?next=' + return_path

    context = {
        'is_owner': True,
        'profile_name': request.user.username,
        'storage_form': form,
        'view': 'storage',
        'profile_view': 'materials',
    }

    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect(return_path)

    else:
        return render(request, 'herders/essence_storage.html', context)


@login_required()
def monster_instance_add(request, profile_name):
    return_path = request.GET.get(
        'next',
        reverse('herders:profile', kwargs={'profile_name': profile_name, 'view_mode': 'list'})
    )
    form = AddMonsterInstanceForm(request.POST or None)

    if form.is_valid() and request.method == 'POST':
        # Create the monster instance
        new_monster = form.save(commit=False)
        new_monster.owner = request.user.summoner
        new_monster.save()

        messages.success(request, 'Added %s to your collection.' % new_monster)
        return redirect(return_path)
    else:
        # Re-show same page but with form filled in and errors shown
        context = {
            'profile_name': profile_name,
            'add_monster_form': form,
            'return_path': return_path,
            'is_owner': True,
            'view': 'profile',
        }
        return render(request, 'herders/profile/profile_monster_add.html', context)


def monster_instance_view(request, profile_name, instance_id):
    context = {
        'view': 'profile',
    }
    return render(request, 'herders/unimplemented.html')

@login_required()
def monster_instance_edit(request, profile_name, instance_id):
    return_path = request.GET.get(
        'next',
        reverse('herders:profile', kwargs={'profile_name': profile_name, 'view_mode': 'list'})
    )

    monster = get_object_or_404(MonsterInstance, pk=instance_id)
    is_owner = monster.owner == request.user.summoner or request.user.is_superuser

    form = EditMonsterInstanceForm(request.POST or None, instance=monster)
    form.helper.form_action = request.path + '?next=' + return_path

    context = {
        'profile_name': request.user.username,
        'return_path': return_path,
        'monster': monster,
        'is_owner': is_owner,
        'edit_monster_form': form,
        'view': 'profile',
    }

    if is_owner:
        if request.method == 'POST':
            if form.is_valid():
                monster = form.save(commit=False)
                monster.save()

                messages.success(request, 'Saved changes to %s.' % monster)
                return redirect(return_path)
            else:
                # Redisplay form with validation error messages
                context['validation_errors'] = form.non_field_errors()
    else:
        raise PermissionDenied()

    return render(request, 'herders/profile/profile_monster_edit.html', context)


@login_required()
def monster_instance_delete(request, profile_name, instance_id):
    return_path = request.GET.get(
        'next',
        reverse('herders:profile', kwargs={'profile_name': profile_name, 'view_mode': 'list'})
    )
    monster = get_object_or_404(MonsterInstance, pk=instance_id)

    # Check for proper owner before deleting
    if request.user.summoner == monster.owner:
        monster.delete()
        return redirect(return_path)
    else:
        return HttpResponseForbidden()


@login_required()
def monster_instance_power_up(request, profile_name, instance_id):
    return_path = request.GET.get(
        'next',
        reverse('herders:profile', kwargs={'profile_name': profile_name, 'view_mode': 'list'})
    )

    monster = get_object_or_404(MonsterInstance, pk=instance_id)
    is_owner = monster.owner == request.user.summoner or request.user.is_superuser

    PowerUpFormset = formset_factory(PowerUpMonsterInstanceForm, extra=5, max_num=5)

    if request.method == 'POST':
        formset = PowerUpFormset(request.POST)
    else:
        formset = PowerUpFormset()

    context = {
        'profile_name': request.user.username,
        'return_path': return_path,
        'monster': monster,
        'is_owner': is_owner,
        'power_up_formset_action': request.path + '?next=' + return_path,
        'power_up_formset': formset,
        'view': 'profile',
    }

    food_monsters = []
    validation_errors = {}

    if is_owner:
        if request.method == 'POST':
            # return render(request, 'herders/view_post_data.html', {'post_data': request.POST})
            if formset.is_valid():
                # Create list of submitted food monsters
                for instance in formset.cleaned_data:
                    # Some fields may be blank if user skipped a form input or didn't fill in all 5
                    if instance:
                        food_monsters.append(instance['monster'])

                # Check that all food monsters are unique - This is done whether or not user bypassed evolution checks
                if len(food_monsters) != len(set(food_monsters)):
                    validation_errors['food_monster_unique'] = "You submitted duplicate food monsters. Please select unique monsters for each slot."

                # Check that monster is not being fed to itself
                for food in food_monsters:
                    if food == monster:
                        validation_errors['base_food_same'] = "You can't feed a monster to itself. "

                is_evolution = request.POST.get('evolve', False)

                # Perform validation checks for evolve action
                if is_evolution:

                    # Check constraints on evolving (or not, if form element was set)
                    if not request.POST.get('ignore_errors', False):
                        # Check monster level and stars
                        if monster.stars >= 6:
                            validation_errors['base_monster_stars'] = "%s is already at 6 stars." % monster.monster.name

                        if monster.level != monster.max_level_from_stars():
                            validation_errors['base_monster_level'] = "%s is not at max level for the current star rating (Lvl %s)." % (monster.monster.name, monster.max_level_from_stars())

                        # Check number of fodder monsters
                        if len(food_monsters) < monster.stars:
                            validation_errors['food_monster_quantity'] = "Evolution requres %s food monsters." % monster.stars

                        # Check fodder star ratings - must be same as monster
                        for food in food_monsters:
                            if food.stars != monster.stars:
                                if 'food_monster_stars' not in validation_errors:
                                    validation_errors['food_monster_stars'] = "All food monsters must be %s stars." % monster.stars
                    else:
                        # Record state of ignore evolve rules for form redisplay
                        context['ignore_evolve_checked'] = True

                    # Perform the stars++ if no errors
                    if not validation_errors:
                        # Level up stars
                        monster.stars += 1
                        monster.level = 1
                        monster.save()
                        messages.success(request, 'Successfully evolved %s to %s<span class="glyphicon glyphicon-star"></span>' % (monster.monster.name, monster.stars), extra_tags='safe')

                if not validation_errors:
                    # Delete the submitted monsters
                    for food in food_monsters:
                        if food.owner == request.user.summoner:
                            messages.success(request, 'Deleted %s' % food)
                            food.delete()
                        else:
                            raise PermissionDenied("Trying to delete a monster you don't own")

                    # Redirect back to return path if evolved, or go to edit screen if power up
                    if is_evolution:
                        return redirect(return_path)
                    else:
                        return redirect(
                            reverse('herders:monster_instance_edit', kwargs={'profile_name':profile_name, 'instance_id': instance_id}) +
                            '?next=' + return_path
                        )
            else:
                context['form_errors'] = formset.non_field_errors()  # Not sure if this will ever happen unless someone tries to be tricksy with form input values

    else:
        raise PermissionDenied("Trying to power up or evolve a monster you don't own")

    # Any errors in the form will fall through to here and be displayed
    context['validation_errors'] = validation_errors
    return render(request, 'herders/profile/profile_power_up.html', context)


@login_required()
def monster_instance_awaken(request, profile_name, instance_id):
    return_path = request.GET.get(
        'next',
        reverse('herders:profile', kwargs={'profile_name': profile_name, 'view_mode': 'list'})
    )
    monster = get_object_or_404(MonsterInstance, pk=instance_id)
    is_owner = monster.owner == request.user.summoner or request.user.is_superuser

    form = AwakenMonsterInstanceForm(request.POST or None)
    form.helper.form_action = request.path + '?next=' + return_path

    context = {
        'profile_name': request.user.username,
        'is_owner': is_owner,  # Because of @login_required decorator
        'return_path': return_path,
        'monster': monster,
        'awaken_monster_form': form,
    }

    if request.method == 'POST' and form.is_valid() and is_owner:
        # Subtract essences from inventory if requested
        if form.cleaned_data['subtract_materials']:
            summoner = Summoner.objects.get(user=request.user)

            if monster.monster.awaken_magic_mats_high:
                summoner.storage_magic_high -= monster.monster.awaken_magic_mats_high
            if monster.monster.awaken_magic_mats_mid:
                summoner.storage_magic_mid -= monster.monster.awaken_magic_mats_mid
            if monster.monster.awaken_magic_mats_low:
                summoner.storage_magic_low -= monster.monster.awaken_magic_mats_low

            if monster.monster.element == Monster.ELEMENT_FIRE:
                if monster.monster.awaken_ele_mats_high:
                    summoner.storage_fire_high -= monster.monster.awaken_ele_mats_high
                if monster.monster.awaken_ele_mats_mid:
                    summoner.storage_fire_mid -= monster.monster.awaken_ele_mats_mid
                if monster.monster.awaken_ele_mats_low:
                    summoner.storage_fire_low -= monster.monster.awaken_ele_mats_low
            elif monster.monster.element == Monster.ELEMENT_WATER:
                if monster.monster.awaken_ele_mats_high:
                    summoner.storage_water_high -= monster.monster.awaken_ele_mats_high
                if monster.monster.awaken_ele_mats_mid:
                    summoner.storage_water_mid -= monster.monster.awaken_ele_mats_mid
                if monster.monster.awaken_ele_mats_low:
                    summoner.storage_water_low -= monster.monster.awaken_ele_mats_low
            elif monster.monster.element == Monster.ELEMENT_WIND:
                if monster.monster.awaken_ele_mats_high:
                    summoner.storage_wind_high -= monster.monster.awaken_ele_mats_high
                if monster.monster.awaken_ele_mats_mid:
                    summoner.storage_wind_mid -= monster.monster.awaken_ele_mats_mid
                if monster.monster.awaken_ele_mats_low:
                    summoner.storage_wind_low -= monster.monster.awaken_ele_mats_low
            elif monster.monster.element == Monster.ELEMENT_DARK:
                if monster.monster.awaken_ele_mats_high:
                    summoner.storage_dark_high -= monster.monster.awaken_ele_mats_high
                if monster.monster.awaken_ele_mats_mid:
                    summoner.storage_dark_mid -= monster.monster.awaken_ele_mats_mid
                if monster.monster.awaken_ele_mats_low:
                    summoner.storage_dark_low -= monster.monster.awaken_ele_mats_low
            elif monster.monster.element == Monster.ELEMENT_LIGHT:
                if monster.monster.awaken_ele_mats_high:
                    summoner.storage_light_high -= monster.monster.awaken_ele_mats_high
                if monster.monster.awaken_ele_mats_mid:
                    summoner.storage_light_mid -= monster.monster.awaken_ele_mats_mid
                if monster.monster.awaken_ele_mats_low:
                    summoner.storage_light_low -= monster.monster.awaken_ele_mats_low

            summoner.save()

        # Perform the awakening by instance's monster source ID
        monster.monster = monster.monster.awakens_to
        monster.save()

        return redirect(return_path)

    else:
        # Retreive list of awakening materials from summoner profile
        summoner = Summoner.objects.get(user=request.user)

        available_materials = {
            'storage_magic_low': summoner.storage_magic_low,
            'storage_magic_mid': summoner.storage_magic_mid,
            'storage_magic_high': summoner.storage_magic_high
        }

        if monster.monster.element == Monster.ELEMENT_FIRE:
            available_materials['storage_ele_low'] = summoner.storage_fire_low
            available_materials['storage_ele_mid'] = summoner.storage_fire_mid
            available_materials['storage_ele_high'] = summoner.storage_fire_high
        elif monster.monster.element == Monster.ELEMENT_WATER:
            available_materials['storage_ele_low'] = summoner.storage_water_low
            available_materials['storage_ele_mid'] = summoner.storage_water_mid
            available_materials['storage_ele_high'] = summoner.storage_water_high
        elif monster.monster.element == Monster.ELEMENT_WIND:
            available_materials['storage_ele_low'] = summoner.storage_wind_low
            available_materials['storage_ele_mid'] = summoner.storage_wind_mid
            available_materials['storage_ele_high'] = summoner.storage_wind_high
        elif monster.monster.element == Monster.ELEMENT_DARK:
            available_materials['storage_ele_low'] = summoner.storage_dark_low
            available_materials['storage_ele_mid'] = summoner.storage_dark_mid
            available_materials['storage_ele_high'] = summoner.storage_dark_high
        elif monster.monster.element == Monster.ELEMENT_LIGHT:
            available_materials['storage_ele_low'] = summoner.storage_light_low
            available_materials['storage_ele_mid'] = summoner.storage_light_mid
            available_materials['storage_ele_high'] = summoner.storage_light_high

        context['available_materials'] = available_materials

        return render(request, 'herders/profile/profile_monster_awaken.html', context)


@login_required
def fusion_progress(request, profile_name):
    return_path = request.GET.get(
        'next',
        reverse('herders:fusion', kwargs={'profile_name': profile_name})
    )
    summoner = get_object_or_404(Summoner, user__username=profile_name)
    is_owner = summoner == request.user.summoner or request.user.is_superuser

    context = {
        'view': 'fusion',
        'profile_name': profile_name,
        'return_path': return_path,
        'is_owner': is_owner,
    }

    fusions = Fusion.objects.all().select_related()
    progress = []

    for fusion in fusions:
        level = 10 + fusion.stars * 5
        ingredients = []

        # Check if fusion has been completed already
        fusion_complete = MonsterInstance.objects.filter(
            Q(owner=summoner), Q(monster=fusion.product) | Q(monster=fusion.product.awakens_to)
        ).count() > 0

        # Scan summoner's collection for instances each ingredient
        for ingredient in fusion.ingredients.all():
            owned_ingredients = MonsterInstance.objects.filter(
                Q(owner=summoner),
                Q(monster=ingredient) | Q(monster=ingredient.awakens_from),
            ).order_by('-stars', '-level', '-monster__is_awakened')

            # Determine if each individual requirement is met using highest evolved/leveled monster
            if len(owned_ingredients) > 0:
                acquired = True
                evolved = owned_ingredients[0].stars >= fusion.stars
                leveled = owned_ingredients[0].level >= level
                awakened = owned_ingredients[0].monster == ingredient
                complete = acquired & evolved & leveled & awakened
            else:
                acquired = False
                evolved = False
                leveled = False
                awakened = False
                complete = False

            ingredient_progress = {
                'instance': ingredient,
                'owned': owned_ingredients,
                'complete': complete,
                'acquired': acquired,
                'evolved': evolved,
                'leveled': leveled,
                'awakened': awakened,
            }
            ingredients.append(ingredient_progress)

        fusion_ready = True
        for i in ingredients:
            if not i['complete']:
                fusion_ready = False

        progress.append({
            'instance': fusion.product,
            'acquired': fusion_complete,
            'stars': fusion.stars,
            'level': level,
            'cost': fusion.cost,
            'ingredients': ingredients,
            'essences_missing': essences_missing(summoner, ingredients),
            'ready': fusion_ready,
        })

        essences_missing(summoner, ingredients)

    context['fusions'] = progress

    return render(request, 'herders/profile/profile_fusion.html', context)


@login_required
def teams(request, profile_name):
    return_path = request.GET.get(
        'next',
        reverse('herders:fusion', kwargs={'profile_name': profile_name})
    )
    summoner = get_object_or_404(Summoner, user__username=profile_name)
    is_owner = summoner == request.user.summoner or request.user.is_superuser
    add_team_group_form = AddTeamGroupForm()

    # Get team objects for the summoner
    team_groups = TeamGroup.objects.filter(owner=summoner)

    context = {
        'view': 'teams',
        'profile_name': profile_name,
        'return_path': return_path,
        'is_owner': is_owner,
        'team_groups': team_groups,
        'add_team_group_form': add_team_group_form,
    }

    return render(request, 'herders/profile/teams/teams_base.html', context)


@login_required
def team_group_add(request, profile_name):
    return_path = request.GET.get(
        'next',
        reverse('herders:teams', kwargs={'profile_name': profile_name})
    )
    summoner = get_object_or_404(Summoner, user__username=profile_name)
    is_owner = summoner == request.user.summoner or request.user.is_superuser

    form = AddTeamGroupForm(request.POST or None)

    if is_owner:
        if form.is_valid() and request.method == 'POST':
            # Create the monster instance
            new_group = form.save(commit=False)
            new_group.owner = request.user.summoner
            new_group.save()

        return redirect(return_path)
    else:
        return PermissionDenied("Attempting to add group to profile you don't own.")


@login_required
def team_group_delete(request, profile_name, group_id):
    return_path = request.GET.get(
        'next',
        reverse('herders:teams', kwargs={'profile_name': profile_name})
    )

    summoner = get_object_or_404(Summoner, user__username=profile_name)
    is_owner = summoner == request.user.summoner or request.user.is_superuser
    team_group = TeamGroup.objects.get(pk=group_id)

    form = DeleteTeamGroupForm(request.POST or None)
    form.helper.form_action = request.path
    form.fields['reassign_group'].queryset = TeamGroup.objects.filter(owner=summoner).exclude(pk=group_id)

    context = {
        'view': 'teams',
        'profile_name': profile_name,
        'return_path': return_path,
        'is_owner': is_owner,
        'form': form,
    }

    if is_owner:
        if request.method == 'POST' and form.is_valid():
            team_list = Team.objects.filter(group__pk=group_id)

            if request.POST.get('delete', False):
                team_list.delete()
            else:
                new_group = form.cleaned_data['reassign_group']
                for team in team_list:
                    team.group = new_group
                    team.save()

        if team_group.team_set.count() > 0:
            return render(request, 'herders/profile/teams/team_group_delete.html', context)
        else:
            messages.success(request, 'Deleted team group %s' % team_group.name)
            team_group.delete()
            return redirect(return_path)
    else:
        return PermissionDenied()


@login_required
def team_detail(request, profile_name, team_id):
    return_path = request.GET.get(
        'next',
        reverse('herders:fusion', kwargs={'profile_name': profile_name})
    )
    summoner = get_object_or_404(Summoner, user__username=profile_name)
    is_owner = summoner == request.user.summoner or request.user.is_superuser

    team = get_object_or_404(Team, pk=team_id)

    context = {
        'view': 'teams',
        'profile_name': profile_name,
        'return_path': return_path,
        'is_owner': is_owner,
        'team': team,
    }

    return render(request, 'herders/profile/teams/team_detail.html', context)


@login_required
def team_edit(request, profile_name, team_id=None):
    return_path = reverse('herders:teams', kwargs={'profile_name': profile_name})
    if team_id:
        team = Team.objects.get(pk=team_id)
        edit_form = EditTeamForm(request.POST or None, instance=team)
    else:
        edit_form = EditTeamForm(request.POST or None)

    summoner = get_object_or_404(Summoner, user__username=profile_name)
    is_owner = summoner == request.user.summoner or request.user.is_superuser

    # Limit form choices to objects owned by the current user.
    edit_form.fields['group'].queryset = TeamGroup.objects.filter(owner=summoner)
    edit_form.fields['leader'].queryset = MonsterInstance.objects.filter(owner=summoner)
    edit_form.fields['roster'].queryset = MonsterInstance.objects.filter(owner=summoner)
    edit_form.helper.form_action = request.path + '?next=' + return_path

    context = {
        'profile_name': request.user.username,
        'return_path': return_path,
        'is_owner': is_owner,
        'edit_team_form': edit_form,
        'view': 'teams',
    }

    if is_owner:
        if request.method == 'POST':
            if edit_form.is_valid():
                team = edit_form.save()
                messages.success(request, 'Saved changes to %s - %s.' % (team.group, team))

                return redirect(return_path + '#' + team.pk.hex)
            else:
                # Redisplay form with validation error messages
                context['validation_errors'] = edit_form.non_field_errors()
    else:
        raise PermissionDenied()

    return render(request, 'herders/profile/teams/team_edit.html', context)


@login_required
def team_delete(request, profile_name, team_id):
    return_path = request.GET.get(
        'next',
        reverse('herders:teams', kwargs={'profile_name': profile_name})
    )
    team = get_object_or_404(Team, pk=team_id)

    # Check for proper owner before deleting
    if request.user.summoner == team.group.owner:
        team.delete()
        messages.success(request, 'Deleted team %s - %s.' % (team.group, team))
        return redirect(return_path)
    else:
        return HttpResponseForbidden()


def bestiary(request):
    context = {
        'view': 'bestiary',
    }

    monster_list = cache.get('bestiary')

    if monster_list is None:
        monster_list = Monster.objects.select_related('awakens_from', 'awakens_to').all()
        cache.set('bestiary', monster_list, 300)

    context['monster_list'] = monster_list

    return render(request, 'herders/bestiary.html', context)


def bestiary_detail(request, monster_id):
    context = {
        'view': 'bestiary',
    }
    return render(request, 'herders/unimplemented.html')


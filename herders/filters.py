import django_filters
from django.db.models import Q

from bestiary.models import Monster, SkillEffect, Skill, LeaderSkill, ScalingStat, RuneCraft, Rune
from .models import MonsterInstance, MonsterTag, RuneInstance, ArtifactInstance, RuneCraftInstance


class MonsterInstanceFilter(django_filters.FilterSet):
    monster__name = django_filters.CharFilter(method='filter_monster__name')
    tags__pk = django_filters.ModelMultipleChoiceFilter(queryset=MonsterTag.objects.all(), to_field_name='pk', conjoined=True)
    monster__element = django_filters.MultipleChoiceFilter(choices=Monster.ELEMENT_CHOICES)
    monster__archetype = django_filters.MultipleChoiceFilter(choices=Monster.ARCHETYPE_CHOICES)
    monster__awaken_level = django_filters.MultipleChoiceFilter(choices=Monster.AWAKEN_CHOICES)
    priority = django_filters.MultipleChoiceFilter(choices=MonsterInstance.PRIORITY_CHOICES)
    monster__leader_skill__attribute = django_filters.MultipleChoiceFilter(choices=LeaderSkill.ATTRIBUTE_CHOICES)
    monster__leader_skill__area = django_filters.MultipleChoiceFilter(choices=LeaderSkill.AREA_CHOICES)
    monster__skills__scaling_stats__pk = django_filters.ModelMultipleChoiceFilter(queryset=ScalingStat.objects.all(), to_field_name='pk', conjoined=True)
    monster__skills__effect__pk = django_filters.ModelMultipleChoiceFilter(queryset=SkillEffect.objects.all(), method='filter_monster__skills__effect__pk')
    monster__skills__cooltime = django_filters.CharFilter(method='filter_bypass')
    monster__skills__hits = django_filters.CharFilter(method='filter_bypass')
    monster__skills__passive = django_filters.BooleanFilter(method='filter_bypass')
    monster__skills__aoe = django_filters.BooleanFilter(method='filter_bypass')
    effects_logic = django_filters.BooleanFilter(method='filter_bypass')
    monster__fusion_food = django_filters.BooleanFilter(method='filter_monster__fusion_food')
    default_build__active_rune_sets = django_filters.MultipleChoiceFilter(choices=Rune.TYPE_CHOICES, method='filter_default_build__active_rune_sets')

    class Meta:
        model = MonsterInstance
        fields = {
            'monster__name': ['exact'],
            'tags__pk': ['exact'],
            'stars': ['gte', 'lte'],
            'level': ['gte', 'lte'],
            'monster__element': ['exact'],
            'monster__archetype': ['exact'],
            'monster__awaken_level': ['exact'],
            'priority': ['exact'],
            'monster__natural_stars': ['gte', 'lte'],
            'monster__leader_skill__attribute': ['exact'],
            'monster__leader_skill__area': ['exact'],
            'monster__skills__effect__pk': ['exact'],
            'monster__skills__scaling_stats__pk': ['exact'],
            'monster__skills__passive': ['exact'],
            'monster__skills__aoe': ['exact'],
            'effects_logic': ['exact'],
            'fodder': ['exact'],
            'in_storage': ['exact'],
            'monster__fusion_food': ['exact'],
            'default_build__active_rune_sets': ['in'],
        }

    def filter_monster__name(self, queryset, name, value):
        if value:
            return queryset.filter(
                Q(monster__name__icontains=value)
                | Q(monster__awakens_from__name__icontains=value)
                | Q(monster__awakens_from__awakens_from__name__icontains=value)
                | Q(monster__awakens_to__name__icontains=value)
            )
        else:
            return queryset
    
    def filter_default_build__active_rune_sets(self, queryset, name, value):
        if value:
            pks = []
            queryset = queryset.filter(default_build__isnull=False)
            for q in queryset:
                if all(int(v) in q.default_build.active_rune_sets for v in value):
                    pks.append(q.pk)

            return queryset.filter(pk__in=pks)
        else:
            return queryset

    def filter_monster__fusion_food(self, queryset, name, value):
        if value:
            return queryset.filter(monster__fusion_food=True).exclude(ignore_for_fusion=True)
        else:
            return queryset.filter(Q(monster__fusion_food=False) | Q(ignore_for_fusion=True))

    def filter_monster__skills__effect__pk(self, queryset, name, value):
        old_filtering = self.form.cleaned_data.get('effects_logic', False)
        stat_scaling = self.form.cleaned_data.get('monster__skills__scaling_stats__pk', [])
        passive = self.form.cleaned_data.get('monster__skills__passive', None)
        aoe = self.form.cleaned_data.get('monster__skills__aoe', None)

        try:
            [min_cooltime, max_cooltime] = self.form.cleaned_data['monster__skills__cooltime'].split(',')
            min_cooltime = int(min_cooltime)
            max_cooltime = int(max_cooltime)
        except:
            min_cooltime = None
            max_cooltime = None

        try:
            [min_num_hits, max_num_hits] = self.form.cleaned_data['monster__skills__hits'].split(',')
            min_num_hits = int(min_num_hits)
            max_num_hits = int(max_num_hits)
        except:
            min_num_hits = None
            max_num_hits = None

        if old_filtering:
            # Filter if any skill on the monster has the designated fields
            for effect in value:
                queryset = queryset.filter(monster__skills__effect=effect)

            for pk in stat_scaling:
                queryset = queryset.filter(monster__skills__scaling_stats=pk)

            cooltime_filter = Q()
            
            if max_cooltime is not None and max_cooltime > 0:
                cooltime_filter &= Q(monster__skills__cooltime__lte=max_cooltime)
            
            if min_cooltime is not None and min_cooltime > 0:
                cooltime_filter &= Q(monster__skills__cooltime__gte=min_cooltime)

            if min_cooltime == 0 or max_cooltime == 0:
                cooltime_filter |= Q(monster__skills__cooltime__isnull=True)

            if cooltime_filter:
                queryset = queryset.filter(cooltime_filter)

            if max_num_hits:
                queryset = queryset.filter(monster__skills__hits__lte=max_num_hits)

            if min_num_hits:
                queryset = queryset.filter(monster__skills__hits__gte=min_num_hits)
            if passive is not None:
                queryset = queryset.filter(monster__skills__passive=passive)

            if aoe is not None:
                queryset = queryset.filter(monster__skills__aoe=aoe)

            return queryset.distinct()

        else:
            # Filter effects based on effects of each individual skill. This ensures a monster will not show up unless it has
            # the desired effects on the same skill rather than across any skills.
            skills = Skill.objects.all()
            skills_count = skills.count()

            for effect in value:
                skills = skills.filter(effect=effect)

            for pk in stat_scaling:
                skills = skills.filter(scaling_stats=pk)

            cooltime_filter = Q()

            if max_cooltime is not None and max_cooltime > 0:
                cooltime_filter &= Q(cooltime__lte=max_cooltime)
            
            if min_cooltime is not None and min_cooltime > 0:
                cooltime_filter &= Q(cooltime__gte=min_cooltime)

            if min_cooltime == 0 or max_cooltime == 0:
                cooltime_filter |= Q(cooltime__isnull=True)

            if cooltime_filter:
                skills = skills.filter(cooltime_filter)
            
            hits_filter = Q()

            if max_num_hits:
                hits_filter &= Q(hits__lte=max_num_hits)

            if min_num_hits:
                hits_filter &= Q(hits__gte=min_num_hits)

            if hits_filter:
                skills = skills.filter(hits_filter)

            if passive is not None:
                skills = skills.filter(passive=passive)

            if aoe is not None:
                skills = skills.filter(aoe=aoe)

            # no skill filters
            if skills_count == skills.count():
                return queryset.distinct()

            return queryset.filter(monster__skills__in=skills).distinct()

    def filter_bypass(self, queryset, name, value):
        # This field's logic is applied in filter_effects()
        return queryset


class RuneInstanceFilter(django_filters.FilterSet):
    type = django_filters.MultipleChoiceFilter(choices=RuneInstance.TYPE_CHOICES)
    slot = django_filters.MultipleChoiceFilter(choices=((1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 6)))
    quality = django_filters.MultipleChoiceFilter(choices=RuneInstance.QUALITY_CHOICES)
    original_quality = django_filters.MultipleChoiceFilter(choices=RuneInstance.QUALITY_CHOICES)
    main_stat = django_filters.MultipleChoiceFilter(choices=RuneInstance.STAT_CHOICES)
    innate_stat = django_filters.MultipleChoiceFilter(choices=RuneInstance.STAT_CHOICES)
    substats = django_filters.MultipleChoiceFilter(choices=RuneInstance.STAT_CHOICES, method='filter_substats')
    substat_logic = django_filters.BooleanFilter(method='filter_substat_logic')
    substat_reverse = django_filters.BooleanFilter(method='filter_substat_reverse')
    assigned_to = django_filters.BooleanFilter(method='filter_assigned_to')
    is_grindable = django_filters.BooleanFilter(method='filter_is_grindable')
    is_enchantable = django_filters.BooleanFilter(method='filter_is_enchantable')

    class Meta:
        model = RuneInstance
        fields = {
            'type': ['exact'],
            'level': ['exact', 'lte', 'lt', 'gte', 'gt'],
            'stars': ['exact', 'lte', 'lt', 'gte', 'gt'],
            'slot': ['exact'],
            'quality': ['exact'],
            'ancient': ['exact'],
            'original_quality': ['exact'],
            'assigned_to': ['exact'],
            'main_stat': ['exact'],
            'innate_stat': ['exact'],
            'marked_for_sale': ['exact'],
            'has_grind': ['exact', 'lte', 'lt', 'gte', 'gt'],
            'has_gem': ['exact'],
        }

    def __init__(self, *args, **kwargs):
        self.summoner = kwargs.pop('summoner', None)
        super(RuneInstanceFilter, self).__init__(*args, **kwargs)

    def filter_substats(self, queryset, name, value):
        any_substat = self.form.cleaned_data.get('substat_logic', False)
        reverse_substat = self.form.cleaned_data.get('substat_reverse', False)

        if len(value):
            if any_substat:
                if reverse_substat:
                    return queryset.exclude(substats__overlap=value)
                else:
                    return queryset.filter(substats__overlap=value)
            else:
                if reverse_substat:
                    return queryset.exclude(substats__contains=value)
                else:
                    return queryset.filter(substats__contains=value)
        else:
            return queryset

    def filter_substat_logic(self, queryset, name, value):
        # This field is just used to alter the logic of substat filter
        return queryset

    def filter_substat_reverse(self, queryset, name, value):
        # This field is just used to alter the reverse of substat filter
        return queryset

    def filter_assigned_to(self, queryset, name, value):
        return queryset.filter(assigned_to__isnull=not value)

    def filter_is_grindable(self, queryset, name, value):
        if not self.summoner:
            return queryset # AssignRune

        # {
        #     normal: {
        #         swift: [atk%, hp%, spd, res%],
        #         ...
        #     },
        #     ancient: {
        #         swift: [atk%, hp%, spd, res%],
        #         ...
        #     },
        # }
        grinds = {
            RuneCraft.CRAFT_GRINDSTONE: {}, 
            RuneCraft.CRAFT_ANCIENT_GRINDSTONE: {},
        }
        rune_grinds =  RuneCraftInstance.objects.only('type', 'rune', 'stat').filter(
            owner=self.summoner,
            quantity__gte=1,
            type__in=grinds.keys(),
        )

        for re in rune_grinds:
            if re.rune not in grinds[re.type]:
                grinds[re.type][re.rune] = []
            if re.stat not in grinds[re.type][re.rune]:
                grinds[re.type][re.rune].append(re.stat)

        query = Q()
        for key, val in grinds.items():
            for rune, stats in val.items():
                for stat in stats:
                    query |= (Q(ancient=key == RuneCraft.CRAFT_ANCIENT_GRINDSTONE) & Q(type=rune) & ~Q(main_stat=stat) & ~Q(innate_stat=stat))

        if value:
            return queryset.filter(query)
        else:
            return queryset.exclude(query)

    def filter_is_enchantable(self, queryset, name, value):
        if not self.summoner:
            return queryset # AssignRune

        # {
        #     normal: {
        #         swift: [atk%, hp%, spd, res%],
        #         ...
        #     },
        #     ancient: {
        #         swift: [atk%, hp%, spd, res%],
        #         ...
        #     },
        # }
        enchants = {
            RuneCraft.CRAFT_ENCHANT_GEM: {}, 
            RuneCraft.CRAFT_ANCIENT_GEM: {},
        }

        rune_enchants =  RuneCraftInstance.objects.only('type', 'rune', 'stat').filter(
            owner=self.summoner,
            quantity__gte=1,
            type__in=enchants.keys(),
        )

        for re in rune_enchants:
            if re.rune not in enchants[re.type]:
                enchants[re.type][re.rune] = []
            if re.stat not in enchants[re.type][re.rune]:
                enchants[re.type][re.rune].append(re.stat)

        query = Q()
        for key, val in enchants.items():
            for rune, stats in val.items():
                for stat in stats:
                    query |= (Q(ancient=key == RuneCraft.CRAFT_ANCIENT_GEM) & Q(type=rune) & ~Q(main_stat=stat) & ~Q(innate_stat=stat))

        if value:
            return queryset.filter(query)
        else:
            return queryset.exclude(query)


class ArtifactInstanceFilter(django_filters.FilterSet):
    slot = django_filters.MultipleChoiceFilter(
        method='filter_slot',
        choices=ArtifactInstance.NORMAL_ELEMENT_CHOICES + ArtifactInstance.ARCHETYPE_CHOICES
    )
    main_stat = django_filters.MultipleChoiceFilter(choices=ArtifactInstance.MAIN_STAT_CHOICES)
    quality = django_filters.MultipleChoiceFilter(choices=ArtifactInstance.QUALITY_CHOICES)
    original_quality = django_filters.MultipleChoiceFilter(choices=ArtifactInstance.QUALITY_CHOICES)
    assigned = django_filters.BooleanFilter(method='filter_assigned_to')
    effects = django_filters.MultipleChoiceFilter(method='filter_effects', choices=ArtifactInstance.EFFECT_CHOICES)
    effects_logic = django_filters.BooleanFilter(method='filter_bypass')

    class Meta:
        model = ArtifactInstance
        fields = {
            'level': ['exact', 'lte', 'lt', 'gte', 'gt'],
            'quality': ['exact', 'in'],
            'original_quality': ['exact', 'in'],
            'efficiency': ['exact', 'lt', 'gt', 'lte', 'gte'],
        }

    def filter_slot(self, queryset, name, value):
        # Split slot filter value into element/archetype fields and filter on both
        all_elements = [choice[0] for choice in ArtifactInstance.NORMAL_ELEMENT_CHOICES]
        all_archetypes = [choice[0] for choice in ArtifactInstance.ARCHETYPE_CHOICES]

        elements = []
        archetypes = []
        for s in value:
            if s in all_elements:
                elements.append(s)
            elif s in all_archetypes:
                archetypes.append(s)

        return queryset.filter(Q(element__in=elements) | Q(archetype__in=archetypes))

    def filter_effects(self, queryset, name, value):
        any_effect = self.form.cleaned_data.get('effects_logic', False)

        if len(value):
            if any_effect:
                return queryset.filter(effects__overlap=value)
            else:
                return queryset.filter(effects__contains=value)
        else:
            return queryset

    def filter_assigned_to(self, queryset, name, value):
        return queryset.filter(assigned_to__isnull=not value)

    def filter_bypass(self, queryset, name, value):
        return queryset
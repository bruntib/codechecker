<template>
  <select-option
    :id="id"
    title="Guideline / Rule Filter"
    :bus="bus"
    :fetch-items="fetchItems"
    :selected-items="selectedItems"
    :search="search"
    :loading="loading"
    :apply="apply"
    @cancel="cancelGuidelineSelection"
    @select="prevSelectedGuidelines = $event"
    @clear="clear(true)"
    @on-menu-show="selectRuleForGuideline = null"
  >
    <template v-slot:append-toolbar-title>
      <selected-toolbar-title-items
        v-if="selectedToolbarTitleItems.length"
        :value="selectedToolbarTitleItems"
      />
    </template>

    <template
      v-slot:menu-content="{
        items,
        prevSelectedItems,
        cancel: cancelItemSelection,
        select
      }"
    >
      <v-menu
        v-model="selectRuleMenu"
        content-class="select-rule-menu"
        :close-on-content-click="false"
        :nudge-width="300"
        :max-width="550"
        offset-x
      >
        <template v-slot:activator="{ on: menu }">
          <items
            :items="items"
            :selected-items="prevSelectedItems"
            :search="search"
            :limit="defaultLimit"
            :format="formatGuidelineTitle"
            @apply="apply"
            @cancel="cancelItemSelection"
            @select="select"
            @update:items="items.splice(0, items.length, ...$event)"
          >
            <template v-slot:append-toolbar>
              <bulb-message>
                Use the <v-icon>mdi-cog</v-icon> button beside each guideline
                after hovering on the guideline to specify a rule.
              </bulb-message>
            </template>

            <template v-slot:prepend-count="{ hover, item }">
              <v-tooltip
                v-if="hover || selectRuleForGuideline === item"
                max-width="200"
                right
              >
                <template v-slot:activator="{ on: tooltip }">
                  <v-btn
                    icon
                    small
                    v-on="{ ...tooltip, ...menu }"
                    @click.stop="specifyRule(item)"
                  >
                    <v-icon>mdi-cog</v-icon>
                  </v-btn>
                </template>

                <span>
                  Specify a guideline rule for this guideline to filter reports
                  indicating their violation.
                </span>
              </v-tooltip>
            </template>

            <template v-slot:title="{ item }">
              <v-list-item-title :title="item.title">
                {{ item.title }}
              </v-list-item-title>
            </template>

            <template v-slot:icon>
              <v-icon color="grey">
                mdi-play-circle
              </v-icon>
            </template>
          </items>
        </template>

        <v-card v-if="selectRuleForGuideline" flat>
          <guideline-rule-items
            :namespace="namespace"
            :selected-items="prevSelectedRuleItems"
            :limit="defaultLimit"
            :rules="selectRuleForGuideline.rules"
            @apply="applyRuleSelection"
            @cancel="cancelRuleSelection"
            @select="selectGuidelineRules"
          >
            <template v-slot:icon>
              <v-icon color="grey">
                mdi-tag
              </v-icon>
            </template>
          </guideline-rule-items>
        </v-card>
      </v-menu>
    </template>

    <template>
      <items-selected
        :selected-items="selectedItems"
        @update:select="updateSelectedItems"
      >
        <template v-slot:icon>
          <v-icon color="grey">
            mdi-play-circle
          </v-icon>
        </template>

        <template v-slot:title="{ item }">
          <v-list-item-title :title="titles[item.id]">
            {{ titles[item.id] }}
          </v-list-item-title>
        </template>
      </items-selected>
    </template>
  </select-option>
</template>

<script>
import _ from "lodash";

import { ccService, handleThriftError } from "@cc-api";
import { ReportFilter } from "@cc/report-server-types";

import BulbMessage from "@/components/BulbMessage";
import {
  Items,
  ItemsSelected,
  SelectOption,
  SelectedToolbarTitleItems,
  filterIsChanged
} from "./SelectOption";
import BaseSelectOptionFilterMixin from "./BaseSelectOptionFilter.mixin";
import GuidelineRuleItems from "./GuidelineRuleItems";

export default {
  name: "GuidelineFilter",
  components: {
    GuidelineRuleItems,
    BulbMessage,
    Items,
    ItemsSelected,
    SelectOption,
    SelectedToolbarTitleItems
  },
  mixins: [ BaseSelectOptionFilterMixin ],

  data() {
    return {
      id: "guideline",
      guidelineRuleId: "guideline-rule",
      selectRuleMenu: false,
      selectRuleForGuideline: null,
      prevSelectedGuidelines: [],
      selectedRuleItems: [],
      prevSelectedRuleItems: [],
      search: {
        placeHolder: "Search for guideline names (e.g.: sei-cert)...",
        regexLabel: "Filter by wildcard pattern (e.g.: sei-cert)",
        filterItems: this.filterItems
      }
    };
  },

  computed: {
    titles() {
      return this.selectedItems.reduce((acc, curr) => ({
        ...acc,
        [curr.id]: this.getSelectedGuidelineTitle(curr).title
      }), {});
    },

    selectedToolbarTitleItems() {
      return this.selectedItems.map(item => ({
        title: this.titles[item.id]
      }));
    }
  },

  methods: {
    formatGuidelineItemWithRules(guideline, rules) {
      guideline.title = rules.length
        ? `${guideline.name}:${rules.join(", ")}`
        : guideline.name;

      return guideline;
    },

    formatGuidelineTitle(guideline) {
      return this.formatGuidelineItemWithRules(
        guideline, this.prevSelectedRuleItems);
    },

    getSelectedGuidelineTitle(guideline) {
      return this.formatGuidelineItemWithRules(
        guideline, this.selectedRuleItems);
    },

    guidelineFilterIsChanged() {
      return filterIsChanged(this.prevSelectedGuidelines, this.selectedItems);
    },

    ruleFilterIsChanged() {
      return filterIsChanged(
        this.prevSelectedRuleItems, this.selectedRuleItems);
    },

    updateSelectedItems(selectedGuidelineItems) {
      this.setSelectedItems(selectedGuidelineItems, this.selectedRuleItems);
    },

    getSelectedRunItems(runNames) {
      return Promise.all(runNames.map(async s => ({
        id: s,
        runIds: await ccService.getRunIds(s),
        title: s,
        count: "N/A"
      })));
    },

    async getSelectedTagItems(/*tags*/) {
      return [];
      // const tagIds = [];
      // const tagWithRunNames = [];
      // tags.forEach(t => {
      //   const id = +t;
      //   if (isNaN(id)) {
      //     tagWithRunNames.push(t);
      //   } else {
      //     tagIds.push(id);
      //   }
      // });

      // // Get tags by tag ids.
      // const tags1 = tagIds.length
      //   ? (await ccService.getTags(null, tagIds)).map(t => {
      //     const time = this.$options.filters.prettifyDate(t.time);
      //     return {
      //       id: t.id.toNumber(),
      //       runName: t.runName,
      //       runId: t.runId.toNumber(),
      //       tagName : t.versionTag || time,
      //       time: time,
      //       title: t.versionTag,
      //       count: "N/A"
      //     };
      //   })
      //   : [];

      // // Get tags by tag names (backward compatibility).
      // const tags2 = tagWithRunNames.length
      //   ? (await Promise.all(tagWithRunNames.map(async s => {
      //     const { runName, tagName } = extractTagWithRunName(s);
      //     const runIds = runName ? await ccService.getRunIds(runName) : null;
      //     const tags = await ccService.getTags(runIds, null, [ tagName ]);
      //     return {
      //       id: tags[0].id,
      //       runName: runName ? runName : tags[0].runName,
      //       runId: tags[0].runId.toNumber(),
      //       time: tags[0].time,
      //       tagName,
      //       title: s,
      //       count: "N/A"
      //     };
      //   })))
      //   : [];

      // return tags1.concat(tags2);
    },

    async initByUrl() {
      let runs = [].concat(this.$route.query[this.id] || []);
      const tags = [].concat(this.$route.query[this.runTagId] || []);

      if (runs.length || tags.length) {
        let selectedTags = [];
        if (tags.length) {
          selectedTags = await this.getSelectedTagItems(tags);

          // Add runs related to tags.
          runs.push(...selectedTags.map(t => t.runName));

          // Filter out duplicates.
          runs = [ ...new Set(runs) ];
        }

        const selectedRuns = await this.getSelectedRunItems(runs);

        await this.setSelectedItems(selectedRuns, selectedTags, false);
      }
    },

    cancelRuleSelection() {
      this.prevSelectedRuleItems = _.cloneDeep(this.selectedRuleItems);
      this.selectRuleMenu = false;
      this.selectRuleForGuideline = null;
    },

    cancelGuidelineSelection() {
      this.prevSelectedGuidelines = _.cloneDeep(this.selectedItems);
      this.cancelRuleSelection();
    },

    apply(selectedGuidelineItems) {

      if (!this.guidelineFilterIsChanged() && !this.ruleFilterIsChanged())
        return;

      this.setSelectedItems(
        selectedGuidelineItems, this.prevSelectedRuleItems);
    },

    applyRuleSelection() {
      this.selectRuleMenu = false;
      this.prevSelectedRuleItems.forEach(() => {
        this.bus.$emit("select", () => true);
      });
    },

    async clear(updateUrl) {
      await this.setSelectedItems([], [], updateUrl);
    },

    selectGuidelineRules(selectedItems) {
      this.prevSelectedRuleItems = _.cloneDeep(selectedItems);
    },

    getUrlState() {
      const guidelineState =
        this.selectedItems.map(item => this.encodeValue(item.id));

      return {
        [this.id]: guidelineState.length ? guidelineState : undefined
      };
      return {
        [this.id]: guidelineState.length ? guidelineState : undefined,
        [this.guidelineRuleId]:
          this.selectedRuleItems.length ? this.selectedRuleItems : undefined
      };
    },

    async setSelectedItems(guidelineItems, ruleItems, updateUrl=true) {
      this.selectedItems = guidelineItems;

      // When removing a guideline with rule item from the selected filter list
      // we need to remove the rules too.
      this.selectedRuleItems = ruleItems.filter(t =>
        guidelineItems.findIndex(s => s.rules.includes(t)) > -1);
      this.prevSelectedRuleItems = _.cloneDeep(this.selectedRuleItems);

      await this.updateReportFilter();

      if (updateUrl) {
        this.$emit("update:url");
      }
    },

    async updateReportFilter() {
      this.reportFilter.guidelines
        = this.selectedItems.length ? this.selectedItems : null;
      this.reportFilter.rules
        = this.selectedRuleItems.length ? this.selectRuleItems : null;
    },

    // onRunIdsChange() {},

    onReportFilterChange(key) {
      if (key === "rules" || key === "guidelines") return;
      this.update();
    },

    fetchItems(opt={}) {
      this.loading = true;

      const limit = opt.limit || this.defaultLimit;
      const offset = 0;

      const reportFilter = new ReportFilter(this.reportFilter);
      reportFilter.runName = opt.query;
      reportFilter.runTag = null;

      return new Promise(resolve => {
        ccService.getClient().getGuidelines(this.runIds, reportFilter,
          this.cmpData, limit, offset, handleThriftError(res => {
            resolve(res);
            this.loading = false;
          }));
      });
    },

    specifyRule(guideline) {
      if (this.selectRuleForGuideline === guideline) {
        this.selectRuleForGuideline = null;
        return;
      }

      this.selectRuleForGuideline = guideline;
      setTimeout(() => this.selectRuleMenu = true, 0);
    }
  }
};
</script>

<style lang="scss" scoped>
.v-tab {
  &.tags:not(.v-tab--disabled) {
    font-weight: bold;
  }

  &.v-tab--active:not(:focus)::before {
    opacity: 0.15;
  }
}
</style>

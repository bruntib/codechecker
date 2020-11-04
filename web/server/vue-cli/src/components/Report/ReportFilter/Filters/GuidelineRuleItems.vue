<template>
  <v-container class="pa-0" fluid>
    <v-progress-linear
      v-if="loading"
      indeterminate
      size="64"
    />

    <items
      :items.sync="filteredRules"
      :selected-items="selectedItems"
      :search="search"
      :limit="defaultLimit"
      @apply="apply"
      @cancel="cancel"
      @select="select"
    >
      <template v-slot:title="{ item }">
        <v-list-item-title :title="item">
          {{ item }}
        </v-list-item-title>
      </template>

      <template v-slot:icon="{ item }">
        <slot name="icon" :item="item" />
      </template>
    </items>
  </v-container>
</template>

<script>
import { mapState } from "vuex";
import _ from "lodash";

import BaseFilterMixin from "./BaseFilter.mixin";
import Items from "./SelectOption/Items";

export default {
  name: "GuidelineRuleItems",
  components: { Items },
  mixins: [ BaseFilterMixin ],
  props: {
    selectedItems: { type: Array, default: null },
    limit: { type: Number, required: true },
    rules: { type: Array, required: true }
  },
  data() {
    return {
      loading: false,
      filteredRules: [],
      search: {
        placeHolder: "Search by rule name...",
        filterItems: this.filterItems
      }
    };
  },
  computed: {
    ...mapState({
      reportFilter(state) {
        return state[this.namespace].reportFilter;
      }
    })
  },
  created() {
    this.filteredRules = _.cloneDeep(this.rules);
  },

  methods: {
    async fetchRules(opt="") {
      return this.rules.filter(item => item.includes(opt));
    },

    filterItems(value) {
      return this.fetchRules(value);
    },

    apply() {
      this.$emit("apply");
    },

    select(selectedItems) {
      this.$emit("select", selectedItems);
    },

    cancel() {
      this.$emit("cancel");
    }
  }
};
</script>

<style lang="scss" scoped>
::v-deep .v-date-picker-table {
  height: 210px;
}
</style>

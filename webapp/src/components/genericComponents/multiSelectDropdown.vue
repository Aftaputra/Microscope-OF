<template>
  <div ref="multiselect" class="multi-select">
    <div class="dropdown-top" :class="{ open: isOpen }" @click="isOpen = !isOpen">
      <span class="dropdown-top-text">{{ title }}</span>
      <span>{{ arrow }}</span>
    </div>

    <div v-if="isOpen" class="dropdown-menu">
      <button class="text-button" @click="selectAll">Select All</button>
      <button class="text-button" @click="selectNone">Select None</button>
      <hr class="dropdown-separator" />
      <label v-for="option in options" :key="option" class="dropdown-item">
        <input
          type="checkbox"
          class="uk-checkbox"
          :value="option"
          :checked="modelValue.includes(option)"
          @change="toggleOption(option)"
        />
        {{ option }}
      </label>
    </div>
  </div>
</template>

<script>
export default {
  name: "MultiSelectDropdown",

  props: {
    modelValue: {
      type: Array,
      default: () => [],
    },
    options: {
      type: Array,
      default: () => [],
    },
    title: {
      type: String,
      default: "Filter",
    },
  },

  emits: ["update:modelValue"],

  data() {
    return {
      isOpen: false,
    };
  },

  computed: {
    arrow() {
      return this.isOpen ? "▲" : "▼";
    },
  },

  mounted() {
    window.addEventListener("click", this.handleClickOutside);
  },

  beforeUnmount() {
    window.removeEventListener("click", this.handleClickOutside);
  },

  methods: {
    handleClickOutside(event) {
      if (!this.$refs.multiselect.contains(event.target)) {
        this.isOpen = false;
      }
    },
    toggleOption(value) {
      const selected = [...this.modelValue];

      const index = selected.indexOf(value);

      if (index > -1) {
        selected.splice(index, 1);
      } else {
        selected.push(value);
      }

      this.$emit("update:modelValue", selected);
    },

    selectAll() {
      this.$emit("update:modelValue", this.options);
    },

    selectNone() {
      this.$emit("update:modelValue", []);
    },
  },
};
</script>

<style lang="less" scoped>
@import url("../../assets/less/variables.less");

.multi-select {
  position: relative;
  width: 250px;
}

.dropdown-top {
  border: 1px solid #ccc;
  padding: 8px 12px;
  border-radius: 4px;
  cursor: pointer;
  background: #f5f5f5;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.dropdown-top-text {
  color: @global-primary-background;
}

.dropdown-top.open {
  border-radius: 4px 4px 0 0;
}

.dropdown-menu {
  position: absolute;
  left: 0;
  right: 0;
  border-left: 1px solid #ccc;
  border-right: 1px solid #ccc;
  border-bottom: 1px solid #ccc;
  border-radius: 0 0 4px 4px;
  background: #f5f5f5;
  max-height: 250px;
  overflow-y: auto;
  z-index: 1000;
}

.text-button {
  display: block;
  background: none;
  border: none;
  padding: 8px 10px;
  cursor: pointer;
  width: 100%;
  text-align: left;
  font-weight: 600;
}

.dropdown-item {
  display: block;
  padding: 8px 12px;
  cursor: pointer;
}

.text-button:hover,
.dropdown-item:hover {
  background: #fff;
}

.dropdown-separator {
  margin: 5px;
}
</style>

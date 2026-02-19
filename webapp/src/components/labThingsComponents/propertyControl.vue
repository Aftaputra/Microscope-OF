<template>
  <input-from-schema
    v-model="modelValue"
    :data-schema="propertyDescription"
    :label="label"
    :animate="animate"
    :options="options"
    :step="step"
    @request-update="readProperty"
    @send-value="writeProperty"
    @animation-shown="resetAnimate"
  />
</template>

<script>
import { formatValue } from "@/js_utils/formatter.mjs";
import InputFromSchema from "./inputFromSchema.vue";

export default {
  name: "PropertyControl",

  components: {
    InputFromSchema,
  },

  props: {
    label: {
      type: String,
      default: "",
    },
    propertyName: {
      type: String,
      required: true,
    },
    thingName: {
      type: String,
      required: true,
    },
    readBack: {
      type: Boolean,
      required: false,
      default: false,
    },
    readBackDelay: {
      type: Number,
      default: 1000,
      required: false,
    },
    options: {
      type: Object,
      default: null,
      required: false,
    },
    step: {
      type: Number,
      default: null,
      required: false,
    },
  },

  data() {
    return {
      modelValue: undefined,
      animate: false,
    };
  },

  computed: {
    propertyDescription: function () {
      try {
        return this.thingDescription(this.thingName).properties[this.propertyName];
      } catch {
        return undefined;
      }
    },
  },

  watch: {
    propertyDescription: function () {
      // Ensure we read the property once the URL is known
      this.readProperty();
    },
  },

  mounted: function () {
    // Read the property when we're mounted - usually this won't
    // work because the URL isn't set yet. However, it's helpful if
    // the app is reloaded (e.g. from a dev server).
    if (this.modelValue == undefined) {
      this.readProperty();
    }
  },

  methods: {
    readProperty: async function () {
      let data = await this.readThingProperty(this.thingName, this.propertyName);
      this.modelValue = data;
      return data;
    },
    writeProperty: async function (requestedValue) {
      try {
        this.modelValue = requestedValue;
        await this.writeThingProperty(this.thingName, this.propertyName, requestedValue);
        if (this.readBack) {
          await new Promise((r) => setTimeout(r, this.readBackDelay));
          let newVal = await this.readProperty();
          if (newVal == requestedValue) {
            this.animate = true;
          } else {
            this.animate = true;
            await this.modalNotify(
              `Set ${this.label} to ${formatValue(
                newVal,
              )} (closest valid value to requested ${formatValue(requestedValue)}).`,
            );
          }
        } else {
          this.animate = true;
        }
      } catch (error) {
        // Use mixin to display error
        this.modalError(error);
        // Re-read property to try to update to server value
        this.readProperty();
      }
    },
    resetAnimate: function () {
      this.animate = false;
    },
  },
};
</script>

<style scoped></style>

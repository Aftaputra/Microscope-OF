<template>
  <input-from-schema
    v-model="value"
    :data-schema="propertyDescription"
    :label="label"
    :animate="animate"
    @requestUpdate="readProperty"
    @sendValue="writeProperty"
    @animationShown="resetAnimate"
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
  },

  data() {
    return {
      value: undefined,
      animate: false,
    };
  },

  computed: {
    propertyDescription: function() {
      try {
        return this.thingDescription(this.thingName).properties[this.propertyName];
      } catch (error) {
        return undefined;
      }
    },
  },

  watch: {
    propertyDescription: function() {
      // Ensure we read the property once the URL is known
      this.readProperty();
    },
  },

  mounted: function() {
    // Read the property when we're mounted - usually this won't
    // work because the URL isn't set yet. However, it's helpful if
    // the app is reloaded (e.g. from a dev server).
    if (this.value == undefined) {
      this.readProperty();
    }
  },

  methods: {
    readProperty: async function() {
      let data = await this.readThingProperty(this.thingName, this.propertyName);
      this.value = data;
      return data;
    },
    writeProperty: async function(requestedValue) {
      try {
        this.value = requestedValue;
        await this.writeThingProperty(this.thingName, this.propertyName, requestedValue);
        if (this.readBack) {
          await new Promise(r => setTimeout(r, this.readBackDelay));
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
    resetAnimate: function() {
      this.animate = false;
    },
  },
};
</script>

<style scoped></style>

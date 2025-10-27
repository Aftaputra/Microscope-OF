<template>
  <div>
    <label v-if="dataType == 'number'" class="uk-form-label"
      >{{ label }}
      <div class="input-and-buttons-container">
        <input
          v-model="internalValue"
          class="uk-form-small numeric-setting-line-input"
          :class="{ edited: isEdited, flash: animateUpdate }"
          type="number"
          @focusin="focusIn"
          @focusout="focusOut"
          @keydown="keyDown"
          @animationend="animationEnd"
        />
        <sync-property-button @click="requestUpdate" />
      </div>
    </label>
    <div v-if="dataType == 'boolean'" class="input-and-buttons-container">
      <label class="uk-form-label numeric-setting-line-input">
        <input
          ref="checkbox"
          v-model="internalValue"
          class="uk-checkbox"
          type="checkbox"
          @change="sendValue"
        />
        {{ label }}
      </label>
      <sync-property-button @click="requestUpdate" />
    </div>
    <label v-if="dataType == 'number_array'" class="uk-form-label"
      >{{ label }}
      <div class="input-and-buttons-container">
        <input
          v-for="i in valueLength"
          :key="i"
          v-model="internalValue[i - 1]"
          class="uk-form-small numeric-setting-line-input"
          :class="{ edited: isEdited, flash: animateUpdate }"
          type="number"
          @input="updateIsEdited"
          @focusin="focusIn"
          @focusout="focusOut"
          @keydown="keyDown"
          @animationend="animationEnd"
        />
        <sync-property-button @click="requestUpdate" />
      </div>
    </label>
    <label v-if="dataType == 'number_object'" class="uk-form-label"
      >{{ label }}
      <div v-for="(val, key) in value" :key="key">
        <label>{{ internalLabels[key] }}</label>
        <div class="input-and-buttons-container">
          <input
            v-model="internalValue[key]"
            class="uk-form-small numeric-setting-line-input"
            :class="{ edited: isEdited, flash: animateUpdate }"
            type="number"
            @input="updateIsEdited"
            @focusin="focusIn"
            @focusout="focusOut"
            @keydown="keyDown"
            @animationend="animationEnd"
          />
          <sync-property-button @click="requestUpdate" />
        </div>
      </div>
    </label>
    <label v-if="dataType == 'other'" class="uk-form-label"
      >{{ label }}
      <div class="input-and-buttons-container">
        <input
          v-model="internalValue"
          class="uk-form-small numeric-setting-line-input"
          type="text"
          disabled="true"
        />
      </div>
    </label>
  </div>
</template>

<script>
import syncPropertyButton from "./syncPropertyButton.vue";

export default {
  name: "InputFromSchema",

  components: {
    syncPropertyButton,
  },

  props: {
    dataSchema: {
      type: Object,
    },
    value: {
      type: null,
    },
    label: {
      type: String,
      default: "",
    },
    animate: {
      type: Boolean,
      default: false,
    },
  },

  data() {
    return {
      // Initialise with a copy to try to prevent the this.value prop being mutated if
      // the value is an array or object. For future updates we stringify and parse
      // (see resetInternalValue). If we do this here there is a chance we get errors
      // as internalValue is still null when rendering starts.
      internalValue: Array.isArray(this.value)
        ? [...this.value]
        : typeof this.value === "object"
        ? { ...this.value }
        : this.value,
      // Is edited can't be computed as we mutate internalValue
      isEdited: false,
      animateUpdate: false,
    };
  },
  computed: {
    internalLabels: function() {
      if (this.dataType == "number_object") {
        let labels = {};
        for (const key in this.internalValue) {
          labels[key] = this.dataSchema.properties[key].title;
        }
        return labels;
      }
      return [];
    },
    valueLength: function() {
      if (this.dataType == "number_array") {
        if (this.internalValue == undefined) {
          return 0;
        }
        return this.internalValue.length;
      } else {
        return 1;
      }
    },
    dataType: function() {
      let prop = this.dataSchema;
      if (prop == undefined) {
        return "undefined";
      }
      const num_types = ["integer", "float", "number"];
      if (num_types.includes(prop.type)) {
        return "number";
      }
      if (prop.type == "array") {
        if (num_types.includes(prop.items.type)) {
          return "number_array";
        }
        if (Array.isArray(prop.items)) {
          if (prop.items.every(t => num_types.includes(t.type))) {
            return "number_array";
          }
        }
      }
      if (prop.type == "boolean") {
        return "boolean";
      }
      if (prop.type == "object") {
        let numeric = true;
        for (let key in prop.properties) {
          if (!num_types.includes(prop.properties[key].type)) {
            numeric = false;
            break;
          }
        }
        if (numeric) {
          return "number_object";
        }
      }
      return "other";
    },
  },

  watch: {
    value() {
      // Fire updateIsEdited on both value and internal value change,
      // as change in value may not causse internalValue to change.
      this.updateIsEdited();
      this.resetInternalValue();
    },
    internalValue() {
      this.updateIsEdited();
    },
    animate(updated) {
      if (updated) {
        this.animateUpdate = true;
      }
    },
  },

  mounted() {
    if (this.value !== undefined) {
      this.resetInternalValue();
    }
  },

  methods: {
    resetInternalValue: function() {
      // Whenever updatirng th internal value stringify and parse as a form of deepcopy.
      // This ensure that the this.value prop is not mutated for when elements of arrays
      // or objects are updated.
      this.internalValue = JSON.parse(JSON.stringify(this.value));
    },
    requestUpdate: async function() {
      this.$emit("requestUpdate");
    },
    sendValue: async function() {
      this.$emit("sendValue", this.internalValue);
    },
    checkboxUpdated: function() {
      if (this.internalValue != this.$refs.checkbox.checked) {
        this.internalValue = this.$refs.checkbox.checked;
        this.sendValue();
      }
    },
    focusIn: function(event) {
      this.valueOnEnter = event.target.value;
    },
    focusOut: function(event) {
      if (this.valueOnEnter != event.target.value) {
        this.sendValue(event.target.value);
      }
    },
    keyDown: function(event) {
      // Pressing enter should set the property, whether or not we think it's changed.
      if (event.keyCode == 13) {
        this.sendValue();
      }
    },
    updateIsEdited: function() {
      this.isEdited = this.deepStringify(this.internalValue) !== this.deepStringify(this.value);
    },
    animationEnd: function() {
      this.animateUpdate = false;
      this.$emit("animationShown");
    },
    deepStringify: function(val) {
      // Create a json string where all internal numbers are also JSON strings. This is
      // needed to robustly check if the value is updated because the raw value may be a
      // number but anything typed in the input is a string. In the case of arrays or
      // objects even with JSON.stringify we end up comparing ["1", 3] with [1, 3] and
      // find them as not equal.
      if (Array.isArray(val)) {
        return JSON.stringify(val.map(String));
      }
      if (val && typeof val === "object") {
        const normalized = Object.fromEntries(Object.entries(val).map(([k, v]) => [k, String(v)]));
        return JSON.stringify(normalized);
      }
      return JSON.stringify(String(val));
    },
  },
};
</script>

<style scoped>
.input-and-buttons-container {
  display: flex;
  flex-flow: row wrap;
  justify-content: flex-start;
  align-content: stretch;
  align-items: center;
  width: 100%;
}
.numeric-setting-line-input {
  flex-grow: 1;
  margin-left: 5px;
  margin-right: 5px;
  width: 6em;
}
.edited {
  background-color: #fff3cd;
}
@keyframes green-flash {
  0% {
    background-color: #3fda63;
  }
  100% {
    background-color: white;
  }
}
.flash {
  animation: green-flash 0.7s ease;
  /*Without this background-colour chrome will ignore the animation colour.*/
  background-color: white;
}
</style>

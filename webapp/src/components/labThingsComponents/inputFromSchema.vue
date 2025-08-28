<template>
  <div>
    <label v-if="dataType == 'number'" class="uk-form-label"
      >{{ label }}
      <div class="input-and-buttons-container">
        <input
          v-model="internalValue"
          class="uk-form-small numeric-setting-line-input"
          type="number"
          @focusin="focusIn"
          @focusout="focusOut"
          @keydown="keyDown"
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
          type="number"
          @focusin="focusIn"
          @focusout="focusOut"
          @keydown="keyDown"
        />
        <sync-property-button @click="requestUpdate" />
      </div>
    </label>
    <label v-if="dataType == 'number_object'" class="uk-form-label"
      >{{ label }}
      <div v-for="(val, key) in value" :key="key">
        <label>{{internalLabels[key]}}</label>
        <div class="input-and-buttons-container" >
          <input
            v-model="internalValue[key]"
            class="uk-form-small numeric-setting-line-input"
            type="number"
            @focusin="focusIn"
            @focusout="focusOut"
            @keydown="keyDown"
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
    syncPropertyButton
  },

  props: {
    dataSchema: {
      type: Object
    },
    value: {
      type: null
    },
    label: {
      type: String,
      default: ""
    },
  },

  data() {
    return {
      internalValue: this.value,
      valueOnEnter: undefined,
      focused: false
    };
  },

  watch: {
    value(newValue) {
      this.internalValue = newValue;
    }
  },
  computed: {
    internalLabels: function() {
      if (this.dataType == "number_object") {
        let labels = {};
        for (const key in this.internalValue){
          labels[key] = this.dataSchema.properties[key].title
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
    }
  },

  methods: {
    requestUpdate: async function() {
      this.$emit("requestUpdate")
    },
    sendValue: async function() {
      this.$emit("sendValue", this.internalValue)
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
    }
  }
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
</style>

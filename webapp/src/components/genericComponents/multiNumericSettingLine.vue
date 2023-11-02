<template>
  <div>
    <label class="uk-form-label">{{ label }}</label>
    <div class="input-and-buttons-container">
      <input
        v-for="(_v, key) in value"
        :key="key"
        v-model="value[key]"
        class="uk-form-small numeric-setting-line-input"
        type="number"
        @focusin="focusIn"
        @focusout="focusOut"
        @keydown="keyDown"
      />
      <a class="button-next-to-input" @click="readProperty">
        <i class="material-icons">refresh</i>
      </a>
    </div>
  </div>
</template>

<script>
import axios from "axios";

export default {
  name: "MultiNumericSettingLine",

  props: {
    label: {
      type: String,
      required: true
    },
    propertyUrl: {
      type: String,
      required: true
    },
    readBackDelay: {
      type: Number,
      default: undefined,
      required: false
    }
  },

  data: () => {
    return {
      value: {},
      valueOnEnter: undefined
    };
  },

  computed: {
    readBack: function() {
      return this.readBackDelay !== undefined;
    }
  },

  mounted() {
    this.readProperty();
  },

  methods: {
    readProperty: async function() {
      let response = await axios.get(this.propertyUrl);
      this.value = response.data;
      console.log("Read property", this.propertyUrl, response.data);
      return response.data;
    },
    writeProperty: async function() {
      try {
        let requestedValue = Number(this.value);
        await axios.post(this.propertyUrl, requestedValue);
        if (this.readBack) {
          await new Promise(r => setTimeout(r, this.readBackDelay));
          let newVal = await this.readProperty();
          if (newVal == requestedValue) {
            await this.modalNotify(`Set ${this.label} to ${newVal}.`);
          } else {
            await this.modalNotify(
              `Set ${this.label} to ${newVal} (requested ${requestedValue}).`
            );
          }
        } else {
          await this.modalNotify(`Set ${this.label} to ${this.value}.`);
        }
      } catch (error) {
        this.modalError(error); // Let mixin handle error
      }
    },
    focusIn: function(event) {
      this.valueOnEnter = event.target.value;
    },
    focusOut: function(event) {
      if (this.valueOnEnter != event.target.value) {
        this.writeProperty(event.target.value);
      }
    },
    keyDown: function(event) {
      // Pressing enter should set the property, whether or not we think it's changed.
      if (event.keyCode == 13) {
        this.writeProperty();
      }
    }
  }
};
</script>

<style scoped>
.input-and-buttons-container {
  display: table;
  width: 100%;
}
.numeric-setting-line-input {
  display: table-cell;
  width: 100%;
}
.button-next-to-input {
  display: table-cell;
  padding-left: 20px;
  padding-right: 5px;
  vertical-align: middle;
  cursor: pointer;
}
</style>

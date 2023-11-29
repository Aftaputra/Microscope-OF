<template>
  <div>
    <label class="uk-form-label">{{ label }}</label>
    <div v-if="dataType == 'number'" class="input-and-buttons-container">
      <input
        v-model="value"
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
    <div v-if="dataType == 'number_array'" class="input-and-buttons-container">
      <input
        v-for="i in value.length"
        :key="i"
        v-model="value[i - 1]"
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
    <div v-if="dataType == 'number_object'" class="input-and-buttons-container">
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
    <div v-if="dataType == 'other'" class="input-and-buttons-container">
      <input
        :value="value"
        class="uk-form-small numeric-setting-line-input"
        type="text"
        disabled="true"
      />
    </div>
  </div>
</template>

<script>
import axios from "axios";

export default {
  name: "PropertyControl",

  props: {
    label: {
      type: String,
      default: ""
    },
    propertyName: {
      type: String,
      required: true
    },
    thingDescription: {
      type: Object,
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
      value: undefined,
      valueOnEnter: undefined,
      focused: false
    };
  },

  computed: {
    readBack: function() {
      return this.readBackDelay !== undefined;
    },
    propertyDescription: function() {
      try {
        return this.thingDescription.properties[this.propertyName];
      } catch (error) {
        return undefined;
      }
    },
    readPropertyUrl: function() {
      let href = this.formHref("readproperty");
      return this.prependTdBaseUri(href);
    },
    writePropertyUrl: function() {
      let href = this.formHref("writeproperty");
      return this.prependTdBaseUri(href);
    },
    dataType: function() {
      let prop = this.propertyDescription;
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

  watch: {
    readPropertyUrl: function() {
      // Ensure we read the property once the URL is known
      this.readProperty();
    }
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
    formHref: function(op = "readproperty") {
      if (this.thingDescription == undefined) return undefined;
      try {
        let forms = this.propertyDescription.forms;
        let readForm = forms.find(f => f.op == op || f.op.includes(op));
        return readForm.href;
      } catch (error) {
        console.log(
          `Failed to find form for ${op} on ${this.propertyName}`,
          error
        );
        return undefined;
      }
    },
    prependTdBaseUri: function(href) {
      if (href == undefined) return undefined;
      if (href.startsWith("http")) return href;
      if ("base" in this.thingDescription) {
        if (href.startsWith("/")) href = href.slice(1);
        if (!this.thingDescription.base.endsWith("/"))
          this.thingDescription.base += "/";
        return this.thingDescription.base + href;
      }
      return href;
    },
    readProperty: async function() {
      console.log(`Reading property ${this.propertyName}`);
      let response = await axios.get(this.readPropertyUrl);
      console.log(`Read property ${this.propertyName}`);
      this.value = response.data;
      console.log("Read property", this.readPropertyUrl, response.data);
      return response.data;
    },
    writeProperty: async function() {
      try {
        let requestedValue = this.value;
        await axios.post(this.writePropertyUrl, requestedValue);
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
.button-next-to-input {
  flex-grow: 0;
  padding-left: 5px;
  padding-right: 5px;
  vertical-align: middle;
  cursor: pointer;
}
</style>

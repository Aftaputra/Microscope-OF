<template>
  <div>
    <div class="uk-flex">
      <div class="uk-text-bold uk-text-uppercase uk-width-expand">
        {{ name }}
      </div>
      <a
        v-if="selfUpdate"
        href="#"
        class="uk-icon uk-width-auto"
        @click="getFormData()"
        ><i class="material-icons">cached</i></a
      >
    </div>

    <form ref="formContainer" class="uk-form-stacked" @submit.prevent="">
      <div v-for="(field, index) in schema" :key="index">
        <div
          v-if="Array.isArray(field)"
          class="uk-grid-small uk-width-1-1 uk-child-width-expand"
          uk-grid
        >
          <div v-for="(subfield, subindex) in field" :key="subindex">
            <component
              :is="subfield.fieldType"
              v-model="formData[subfield.name]"
              v-bind="subfield"
            >
            </component>
          </div>
        </div>

        <component
          :is="field.fieldType"
          v-model="formData[field.name]"
          v-bind="field"
        >
        </component>
      </div>

      <taskSubmitter
        v-if="isTask"
        :submit-url="submitApiUri"
        :submit-data="formData"
        :submit-label="submitLabel"
        @submit="onTaskSubmit"
        @response="onTaskResponse"
        @error="onTaskError"
      >
      </taskSubmitter>

      <button
        v-else
        type="button"
        class="uk-button uk-button-primary uk-form-small uk-float-right uk-margin-small uk-width-1-1"
        @click="newQuickRequest(formData)"
      >
        {{ submitLabel }}
      </button>
    </form>
  </div>
</template>

<script>
import axios from "axios";

import numberInput from "../fieldComponents/numberInput";
import selectList from "../fieldComponents/selectList";
import textInput from "../fieldComponents/textInput";
import htmlBlock from "../fieldComponents/htmlBlock";
import radioList from "../fieldComponents/radioList";
import checkList from "../fieldComponents/checkList";
import tagList from "../fieldComponents/tagList";
import keyvalList from "../fieldComponents/keyvalList";

import taskSubmitter from "../genericComponents/taskSubmitter";

export default {
  name: "JsonForm",

  components: {
    numberInput,
    selectList,
    textInput,
    htmlBlock,
    radioList,
    checkList,
    tagList,
    keyvalList,
    taskSubmitter
  },

  props: {
    name: {
      type: String,
      required: false,
      default: "Plugin"
    },
    schema: {
      type: Array,
      required: true
    },
    route: {
      type: String,
      required: true
    },
    isTask: {
      type: Boolean,
      required: false,
      default: false
    },
    submitLabel: {
      type: String,
      required: false,
      default: "Submit"
    },
    selfUpdate: {
      type: Boolean,
      required: false,
      default: false
    }
  },

  data: function() {
    return {
      formData: {}
    };
  },

  computed: {
    pluginApiUri: function() {
      return `${this.$store.getters.baseUri}/api/v2/plugins`;
    },

    submitApiUri: function() {
      return this.pluginApiUri + this.route;
    }
  },

  created() {
    this.initialiseFormData();

    if (this.selfUpdate) {
      this.getFormData();
    }
  },

  methods: {
    initialiseFormData() {
      /* 
      This function initialises the form data.
      Limitations in Vue mean that newly created formData properties are not reactive.
      GETting formData values from the server creates the properties, but the form components
      don't get updated because of this limitation.
      Here, we step through the form schema, and properly create reactive properties for each component.
      */
      for (const field of this.schema) {
        if (Array.isArray(field)) {
          var defaultValue; // Initial value of the form component
          for (const subfield of field) {
            // If a default value is given in the schema, use this
            defaultValue = subfield.default ? subfield.default : null;
            this.$set(this.formData, subfield.name, defaultValue);
          }
        } else {
          // If a default value is given in the schema, use this
          defaultValue = field.default ? field.default : null;
          this.$set(this.formData, field.name, defaultValue);
        }
      }
    },

    updateForm(fieldName, value) {
      this.$set(this.formData, fieldName, value);
      this.$emit("input", this.formData);
    },

    getFormData: function() {
      // Send a quick request
      axios
        .get(this.submitApiUri)
        .then(response => {
          console.log(response.data);
          Object.assign(this.formData, response.data);
        })
        .catch(error => {
          this.modalError(error); // Let mixin handle error
        });
    },

    newQuickRequest: function(params) {
      console.log(this.submitApiUri);
      console.log(params);
      // Send a quick request
      axios
        .post(this.submitApiUri, params)
        .then(response => {
          // Do something with the response
          console.log(response);
          // Update the form data if we're self-updating
          if (this.selfUpdate) {
            this.getFormData();
          }
        })
        .catch(error => {
          this.modalError(error); // Let mixin handle error
        });
    },

    onTaskSubmit: function() {},

    onTaskResponse: function(responseData) {
      console.log("Task finished with response data: ", responseData);
      if (this.selfUpdate) {
        this.getFormData();
      }
    },

    onTaskError: function(error) {
      this.modalError(error);
    }
  }
};
</script>

<style scoped>
.flex-container {
  display: flex;
}

.flex-container > div {
  flex-basis: 100%;
}
</style>

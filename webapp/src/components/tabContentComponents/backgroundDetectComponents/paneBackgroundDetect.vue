<template>
  <div class="uk-padding-small">
    <div>
      <ul uk-accordion="multiple: true">
        <li>
          <a class="uk-accordion-title" href="#">Configure</a>
          <div class="uk-accordion-content">
            <input-from-schema
              v-if="backgroundDetectorStatus"
              v-model="backgroundDetectorStatus.settings"
              :data-schema="backgroundDetectorStatus.settings_schema"
              label=""
              @requestUpdate="readSettings"
              @sendValue="writeSettings"
            />
          </div>
        </li>
      </ul>
      <div class="uk-margin">
        <action-button
          thing="camera"
          action="set_background"
          submit-label="Set Background"
          :can-terminate="false"
          :poll-interval="0.1"
          @response="alertBackgroundSet"
          @error="modalError"
        />
      </div>
      <div class="uk-margin">
        <!--Once status is read this should be disabled id not ready..-->
        <action-button
          thing="camera"
          action="image_is_sample"
          submit-label="Check Current Image"
          :isDisabled="!ready"
          :can-terminate="false"
          :poll-interval="0.1"
          @response="alertImageLabel"
          @error="modalError"
        />
      </div>
    </div>
  </div>
</template>

<script>
import ActionButton from "../../labThingsComponents/actionButton.vue";
import InputFromSchema from "../../labThingsComponents/inputFromSchema.vue";

export default {
  components: {
    ActionButton,
    InputFromSchema
  },

  data() {
    return {
      backgroundDetectorStatus: undefined,
    };
  },

  computed: {
    ready() {
      const status = this.backgroundDetectorStatus;
      return status && status.ready === true;
    }
  },

  methods: {
    alertBackgroundSet() {
      this.modalNotify(`Background image has been updated`);
    },
    alertImageLabel(r) {
      let label = r.output[0] ? "sample" : "background";
      this.modalNotify(`Current image is ${label} (${r.output[1]})`);
    },
    readSettings: async function() {
      this.backgroundDetectorStatus = await this.readThingProperty(
        "camera",
        "background_detector_status"
      );
    },
    writeSettings: async function(requestedValue) {
      await this.invokeAction(
        "camera",
        "update_detector_settings",
        {"data": requestedValue}
      );
    }
  },
  async created() {
    this.backgroundDetectorStatus = await this.readThingProperty(
      "camera",
      "background_detector_status"
    );
  }
};
</script>

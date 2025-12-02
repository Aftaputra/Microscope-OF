<template>
  <div v-observe-visibility="visibilityChanged" class="uk-padding-small">
    <div>
      <ul uk-accordion="multiple: true">
        <li>
          <a class="uk-accordion-title" href="#">Configure</a>
          <div class="uk-accordion-content">
            <h4 v-if="backgroundDetectorName" class="detector-name">
              {{ backgroundDetectorName }}
            </h4>
            <input-from-schema
              v-if="backgroundDetectorStatus"
              v-model="backgroundDetectorStatus.settings"
              :data-schema="backgroundDetectorStatus.settings_schema"
              label=""
              :animate="animate"
              @requestUpdate="readSettings"
              @sendValue="writeSettings"
              @animationShown="resetAnimate"
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
        <!--Once status is read this should be disabled if not ready..-->
        <action-button
          thing="camera"
          action="image_is_sample"
          submit-label="Check Current Image"
          :is-disabled="!ready"
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
    InputFromSchema,
  },

  data() {
    return {
      backgroundDetectorStatus: undefined,
      backgroundDetectorName: undefined,
      animate: false,
    };
  },

  computed: {
    ready() {
      const status = this.backgroundDetectorStatus;
      return status && status.ready === true;
    },
  },
  async created() {
    this.backgroundDetectorStatus = await this.readThingProperty(
      "camera",
      "background_detector_status",
    );
  },

  methods: {
    visibilityChanged(isVisible) {
      if (isVisible) {
        this.readSettings();
      }
    },
    alertBackgroundSet() {
      this.modalNotify(`Background image has been updated`);
    },
    alertImageLabel(r) {
      let label = r.output[0] ? "sample" : "background";
      this.modalNotify(`Current image is ${label} (${r.output[1]})`);
    },
    readSettings: async function () {
      this.backgroundDetectorName = await this.readThingProperty("camera", "detector_name");
      this.backgroundDetectorStatus = await this.readThingProperty(
        "camera",
        "background_detector_status",
      );
    },
    writeSettings: async function (requestedValue) {
      await this.invokeAction("camera", "update_detector_settings", { data: requestedValue });
      this.animate = true;
      this.readSettings();
    },
    resetAnimate: function () {
      this.animate = false;
    },
  },
};
</script>
<style scoped lang="less">
.detector-name {
  margin-bottom: 0.5rem;
}
</style>

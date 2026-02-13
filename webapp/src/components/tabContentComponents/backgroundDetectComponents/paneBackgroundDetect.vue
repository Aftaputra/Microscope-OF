<template>
  <div ref="backgroundDetectContent" class="uk-padding-small">
    <div>
      <ul uk-accordion="multiple: true">
        <li>
          <a class="uk-accordion-title" href="#">Configure</a>
          <div class="uk-accordion-content">
            <h4 v-if="backgroundDetectorDisplayName" class="detector-name">
              {{ backgroundDetectorDisplayName }}
            </h4>
            <server-specified-property-control
              v-for="(setting, index) in backgroundDetectorSettings"
              :key="'detector_setting' + index"
              :property-data="setting"
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
import ServerSpecifiedPropertyControl from "../../labThingsComponents/serverSpecifiedPropertyControl.vue";
// vue3 migration
import { useIntersectionObserver } from "@vueuse/core";

export default {
  components: {
    ActionButton,
    ServerSpecifiedPropertyControl
  },

  data() {
    return {
      ready: false,
      backgroundDetectorName: undefined,
      backgroundDetectorDisplayName: undefined,
      backgroundDetectorSettings: [],
      animate: false,
    };
  },

  methods: {
    async safeReadSettings() {
      if (!this.$store.state.connected) return;
      
      try {
        await this.readSettings();
      } catch (error) {
        console.error("Error reading background detector settings:", error);
      }
    },

    visibilityChanged(isVisible) {
      if (isVisible) {
        this.safeReadSettings();
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
      this.backgroundDetectorName = await this.readThingProperty(
        "camera",
        "background_detector_name",
      );
      if (this.backgroundDetectorName) {
        this.ready = await this.readThingProperty(this.backgroundDetectorName, "ready");
        this.backgroundDetectorSettings = await this.readThingProperty(
          this.backgroundDetectorName,
          "settings_ui",
        );
        this.backgroundDetectorDisplayName = await this.readThingProperty(
          this.backgroundDetectorName,
          "display_name",
        );
      }
    },
  },

  mounted() {
    useIntersectionObserver(
      this.$refs.backgroundDetectContent,
      ([{ isIntersecting }]) => {
        this.visibilityChanged(isIntersecting);
      },
      {
        threshold: 0.0,
      },
    );
  },
};
</script>
<style scoped lang="less">
.detector-name {
  margin-bottom: 0.5rem;
}
</style>

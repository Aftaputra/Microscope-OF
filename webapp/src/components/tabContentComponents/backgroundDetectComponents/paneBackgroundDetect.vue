<template>
  <div class="uk-padding-small">
    <div v-show="!backendOK" class="uk-alert-danger">
      The background detect Thing seems to be missing or incompatible.
    </div>
    <div v-show="backendOK">
      <div class="uk-margin">
        <taskSubmitter
          :submit-url="setBackgroundUri"
          submit-label="Set background"
          :can-terminate="false"
          :poll-interval="0.1"
          @response="alertBackgroundSet"
        />
      </div>
      <div class="uk-margin">
        <propertyControl
          thing-name="background_detect"
          property-name="tolerance"
          label="Tolerance"
        />
      </div>
      <div class="uk-margin">
        <propertyControl
          thing-name="background_detect"
          property-name="fraction"
          label="Sample coverage required"
        />
      </div>
      <div class="uk-margin">
        <taskSubmitter
          :submit-url="backgroundFractionUri"
          submit-label="Check current image"
          :can-terminate="false"
          :poll-interval="0.1"
          @response="alertBackgroundFraction"
        />
      </div>
      <div class="uk-margin">
        <taskSubmitter
          :submit-url="labelImageUri"
          submit-label="Label current image"
          :can-terminate="false"
          :poll-interval="0.1"
          @response="alertImageLabel"
        />
      </div>
    </div>
  </div>
</template>

<script>
import taskSubmitter from "../../genericComponents/taskSubmitter";
import propertyControl from "../../labThingsComponents/propertyControl.vue";

export default {
  components: {
    taskSubmitter,
    propertyControl
  },

  computed: {
    labelImageUri() {
      return this.thingActionUrl("background_detect", "image_is_sample");
    },
    backgroundFractionUri() {
      return this.thingActionUrl("background_detect", "background_fraction");
    },
    setBackgroundUri() {
      return this.thingActionUrl("background_detect", "set_background");
    },
    backendOK() {
      return (
        (this.backgroundFractionUri != null) & (this.setBackgroundUri != null)
      );
    }
  },

  methods: {
    alertBackgroundFraction(r) {
      let fraction = r.output;
      // let percentage = (fraction * 100).toFixed(0);
      this.modalNotify(`Current image is ${fraction.toFixed(0)}% background.`);
    },
    alertBackgroundSet() {
      this.modalNotify(`Background image has been updated`);
    },
    alertImageLabel(r) {
      let label = r.output===true? 'sample' : 'background'
      this.modalNotify(`Current image is ${label}`);
    }
  }
};
</script>

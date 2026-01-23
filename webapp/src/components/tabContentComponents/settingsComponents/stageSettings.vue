<template>
  <div id="stageSettings" v-observe-visibility="visibilityChanged" class="uk-width-large">
    The microscope stage is a <b>{{ stageType }}</b>
    <div>
      <div class="uk-margin">
        <p>Your z motor is currently {{ z_inverted }} inverted.</p>
        <p>We expect that moving in +z:</p>
        <ul>
          <li>Moves your objective up, towards the sample and illumination</li>
          <li>Turns the exposed z gear anti-clockwise (when viewed from above)</li>
        </ul>
        <p>If this is not the case, click the button below to switch.</p>
        <div class="uk-margin">
          <div class="uk-margin">
            <action-button
              class="uk-width-1-2"
              thing="stage"
              action="invert_axis_direction"
              :submit-data="{ axis: 'z' }"
              submit-label="Invert z"
              @response="readAxis()"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import ActionButton from "../../labThingsComponents/actionButton.vue";
// vue3 migration
import { markRaw } from "vue";

export default {
  name: "StageSettings",

  components: {
    ActionButton: markRaw(ActionButton),
  },

  data: function () {
    return {
      z_inverted: "",
    };
  },

  computed: {
    stageType: function () {
      return this.thingDescription("stage").title;
    },
  },

  methods: {
    visibilityChanged(isVisible) {
      if (isVisible) {
        this.readAxis();
      }
    },
    async readAxis() {
      let axes_inverted = await this.readThingProperty("stage", "axis_inverted");
      this.z_inverted = axes_inverted["z"] ? "" : "not ";
    },
  },
};
</script>

<style lang="less"></style>

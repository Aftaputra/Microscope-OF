<template>
  <div id="stageSettings" class="uk-width-large" v-observe-visibility="visibilityChanged">
    The microscope stage is a <b>{{ stageType }}</b>
    <div>
      <div class="uk-margin">
        <p>
        <br>
        Your z motor is currently {{ this.z_inverted }} inverted.
        <br>
        <br>
        If you notice that moving in +z moves your objective down,
        or causes your exposed z gear to turn clockwise,
        this is backwards.
        <br>
        <br>
        Click the button below to switch.
        </p>
        <div class="uk-margin">
          <div class="uk-margin">
          <action-button
            class="uk-width-1-2"
            thing="stage"
            action="invert_axis_direction"
            :submit-data="{ axis: 'z' }"
            submit-label="Invert z"
            @response=readAxis()
          />
        </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import ActionButton from "../../labThingsComponents/actionButton.vue";

export default {
  name: "StageSettings",

  components: {
    ActionButton,
  },

  data: function() {
    return {
      z_inverted: "",
    };
  },

  methods:{
    visibilityChanged(isVisible) {
      if (isVisible) {
        this.readAxis();
      }
    },
    async readAxis() {
      let axes_inverted = await this.readThingProperty(
        "stage",
        "axis_inverted"
      );
      this.z_inverted = axes_inverted['z'] ? "" : "not ";
    }
  },

  computed: {
    stageType: function() {
      return this.thingDescription("stage").title;
    }
  }
};
</script>

<style lang="less"></style>

<template>
  <ul uk-accordion="multiple: true">
    <li class="uk-closed">
      <a class="uk-accordion-title" href="#">Position</a>
      <div class="uk-accordion-content">
        <form>
          <!-- Text boxes to set and view position -->
          <div class="input-and-buttons-container">
            <input
              v-for="(_v, key) in setPosition"
              :key="`setPosition_${key}`"
              v-model="setPosition[key]"
              class="uk-form-small numeric-setting-line-input"
              type="number"
              @keyup.enter="startMoveTask"
            />
            <sync-property-button @click="updatePosition" />
          </div>
          <p>
            <action-button
              ref="moveButton"
              thing="stage"
              action="move_absolute"
              :submit-data="setPosition"
              :submit-label="'Move'"
              :can-terminate="true"
              :poll-interval="0.05"
              @finished="moveComplete"
              @error="modalError"
            />
          </p>
        </form>
        <action-button
          thing="stage"
          action="set_zero_position"
          submit-label="Zero Coordinates"
          :can-terminate="false"
          @finished="updatePosition"
          @error="modalError"
        />
      </div>
    </li>
  </ul>
</template>

<script>
import ActionButton from "../../labThingsComponents/actionButton.vue";
import syncPropertyButton from "../../labThingsComponents/syncPropertyButton.vue";

export default {
  name: "PaneControl",

  components: {
    ActionButton,
    syncPropertyButton,
  },

  data: function () {
    return {
      setPosition: null,
      moveLock: false,
    };
  },

  computed: {
    positionStatusUri: function () {
      return this.thingActionUrl("stage", "position");
    },
  },

  async mounted() {
    let self = this;
    // A global signal listener to perform a move action
    this.$root.$on("globalMoveEvent", self.move);
    // A global signal listener to perform a move action in pixels
    this.$root.$on("globalMoveInImageCoordinatesEvent", (x, y, absolute) => {
      this.moveInImageCoordinatesRequest(x, y, absolute);
    });
    // A global signal listener to perform a move in multiples of a step size
    this.$root.$on("globalMoveStepEvent", (x_steps, y_steps, z_steps) => {
      const navigationStepSize = this.$store.state.navigationStepSize;
      const navigationInvert = this.$store.state.navigationInvert;
      const x = x_steps * navigationStepSize.x * (navigationInvert.x ? -1 : 1);
      const y = y_steps * navigationStepSize.y * (navigationInvert.y ? -1 : 1);
      const z = z_steps * navigationStepSize.z * (navigationInvert.z ? -1 : 1);
      this.$root.$emit("globalMoveEvent", x, y, z, false);
    });
    // Update the current position in text boxes
    await this.updatePosition();
  },

  beforeDestroy() {
    // Remove global signal listener to perform a move action
    this.$root.$off("globalMoveEvent");
    this.$root.$off("globalMoveInImageCoordinatesEvent");
    this.$root.$off("globalMoveStepEvent");
  },

  methods: {
    timeout(ms) {
      return new Promise((resolve) => setTimeout(resolve, ms));
    },
    async move(x, y, z, absolute) {
      // Move the stage, by updating the controls and starting a move task
      // This is equivalent to clicking the "move" button.
      if (this.moveLock) return; // Discard move requests if we're already moving
      // NB moveLock is just  boolean flag - it's not as safe as a "proper" lock.
      this.moveLock = true; // This will also be set by the task submitter, but
      // setting it here avoids multiple moves being requested simultaneously.
      if (absolute) {
        this.setPosition = { x: x, y: y, z: z };
      } else {
        await this.updatePosition();
        this.setPosition = {
          x: this.setPosition.x + x,
          y: this.setPosition.y + y,
          z: this.setPosition.z + z,
        };
      }
      await this.timeout(1); // Wait for Vue to update the position
      await this.startMoveTask();
    },
    async startMoveTask() {
      this.moveLock = true;
      await this.$refs.moveButton.startTask();
    },
    moveComplete() {
      this.updatePosition();
      this.moveLock = false;
    },
    async moveInImageCoordinatesRequest(x, y) {
      // If not movement-locked
      if (!this.moveLock) {
        // Lock move requests
        this.moveLock = true;
        const response = await this.invokeAction(
          "camera_stage_mapping",
          "move_in_image_coordinates",
          {
            x: x,
            y: y,
          },
        );
        this.pollUntilComplete(
          response.data.href,
          null, // Nothing to do while ongoing
          this.moveComplete, // Call move complete once done.
          200,
        );
      }
    },

    async updatePosition() {
      this.setPosition = await this.readThingProperty("stage", "position");
    },
  },
};
</script>
<style scoped>
.input-and-buttons-container {
  display: flex;
  flex-flow: column wrap;
  justify-content: flex-start;
  align-content: stretch;
  align-items: center;
  width: 100%;
}
.numeric-setting-line-input {
  flex-grow: 1;
  margin: 5px 0px;
  width: 5em;
  /* Stop Firefox showing input spinners, other
  browsers set with block below */
  -moz-appearance: textfield;
}
/* Chrome, Safari, Edge, Opera */
.numeric-setting-line-input::-webkit-outer-spin-button,
.numeric-setting-line-input::-webkit-inner-spin-button {
  -webkit-appearance: none;
}
</style>

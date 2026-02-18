<!-- This is the main position component for the control tab.

Do not reuse this component until we remove global listeners for move.

This component shows themotor positions in a closed accordion along with the move
and zero position buttons. It also includes the d-pad.
-->
<template>
  <div>
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
          <div class="uk-flex uk-flex-center uk-margin">
            <hr class="uk-divider-small" />
          </div>
        </div>
      </li>
    </ul>

    <stageControlButtons />
  </div>
</template>

<script>
import ActionButton from "../../labThingsComponents/actionButton.vue";
import syncPropertyButton from "../../labThingsComponents/syncPropertyButton.vue";
import stageControlButtons from "./stageControlButtons.vue";
import { eventBus } from "../../../eventBus.js";

export default {
  name: "PaneControl",

  components: {
    ActionButton,
    syncPropertyButton,
    stageControlButtons,
  },

  data: function () {
    return {
      setPosition: null,
      moveLock: false,
      jogging: false,
    };
  },

  computed: {
    positionStatusUri: function () {
      return this.thingActionUrl("stage", "position");
    },
  },

  async mounted() {
    // A global signal listener to perform a move action
    eventBus.on("globalMoveEvent", this.move);
    // A global signal listener to update position text boxes
    eventBus.on("globalUpdatePositionEvent", this.updatePosition);
    // A global signal listener to perform a move action in pixels
    eventBus.on("globalMoveInImageCoordinatesEvent", this.onMoveImage);

    // Update the current position in text boxes
    await this.updatePosition();
  },

  beforeUnmount() {
    // Remove global signal listener to perform a move action
    eventBus.off("globalMoveEvent", this.move);
    eventBus.off("globalUpdatePositionEvent", this.updatePosition);
    eventBus.off("globalMoveInImageCoordinatesEvent", this.onMoveImage);
  },

  methods: {
    timeout(ms) {
      return new Promise((resolve) => setTimeout(resolve, ms));
    },

    onMoveImage(payload) {
      this.moveInImageCoordinatesRequest(payload.x, payload.y, payload.absolute);
    },

    async move(payload) {
      const { x, y, z, absolute } = payload;
      // Move the stage, by updating the controls and starting a move task
      // This is equivalent to clicking the "move" button.
      if (this.moveLock) return; // Discard move requests if we're already moving
      if (this.jogging) return; // Discard move requests if a jog is in progress
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
      await this.$nextTick(); // Wait for Vue to update the position
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

<template>
  <div id="paneNavigate" class="uk-padding-small">
    <div v-if="setPosition">
      <ul uk-accordion="multiple: true">
        <li>
          <a class="uk-accordion-title" href="#">Configure</a>
          <div class="uk-accordion-content">
            <b>STEP SIZE</b>
            <div class="uk-grid-small uk-child-width-1-3" uk-grid>
              <div>
                <label class="uk-form-label" for="form-stacked-text">x</label>
                <div class="uk-form-controls">
                  <input
                    v-model="stepSize.x"
                    class="uk-input uk-form-small"
                    type="number"
                    name="inputStepXy"
                  />
                </div>
                <label class="uk-margin-small-right"
                  ><input
                    v-model="invert.x"
                    class="uk-checkbox"
                    type="checkbox"
                  />
                  Invert x</label
                >
              </div>

              <div>
                <label class="uk-form-label" for="form-stacked-text">y</label>
                <div class="uk-form-controls">
                  <input
                    v-model="stepSize.y"
                    class="uk-input uk-form-small"
                    type="number"
                    name="inputStepY"
                  />
                </div>
                <label class="uk-margin-small-right"
                  ><input
                    v-model="invert.y"
                    class="uk-checkbox"
                    type="checkbox"
                  />
                  Invert y</label
                >
              </div>

              <div>
                <label class="uk-form-label" for="form-stacked-text">z</label>
                <div class="uk-form-controls">
                  <input
                    v-model="stepSize.z"
                    class="uk-input uk-form-small"
                    type="number"
                    name="inputStepZz"
                  />
                </div>
                <label
                  ><input
                    v-model="invert.z"
                    class="uk-checkbox"
                    type="checkbox"
                  />
                  Invert z</label
                >
              </div>
            </div>

            <taskSubmitter
              :submit-url="zeroActionUri"
              :submit-label="'Zero Coordinates'"
              :can-terminate="false"
              @finished="updatePosition"
              @error="modalError"
            ></taskSubmitter>
            <taskSubmitter
              :submit-url="recentreActionUri"
              :submit-label="'Re-centre Stage'"
              :can-terminate="false"
              :requires-confirmation="true"
              :confirmation-message="
                'The stage will now move, and autofocus will be used to find the centre of motion. This requires a sample to be visible in the microscope. OK to proceed?'
              "
              @finished="updatePosition"
              @error="modalError"
            ></taskSubmitter>
          </div>
        </li>

        <li class="uk-open">
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
                <a class="button-next-to-input" @click="updatePosition">
                  <i class="material-icons">refresh</i>
                </a>
              </div>
              <p>
                <taskSubmitter
                  ref="moveTaskSubmitter"
                  :submit-url="absoluteMoveUri"
                  :submit-data="setPosition"
                  :submit-label="'Move'"
                  :can-terminate="false"
                  :poll-interval="0.05"
                  @taskStarted="moveLock = true"
                  @finished="moveLock = false"
                  @error="modalError"
                ></taskSubmitter>
              </p>
            </form>
          </div>
        </li>

        <!--Show autofocus if default plugin is enabled-->
        <li v-show="fastAutofocusUri || normalAutofocusUri" class="uk-open">
          <a class="uk-accordion-title" href="#">Autofocus</a>
          <div class="uk-accordion-content">
            <div class="uk-grid-small uk-child-width-expand" uk-grid>
              <div v-show="!isAutofocusing || isAutofocusing == 1">
                <taskSubmitter
                  v-if="fastAutofocusUri"
                  :submit-url="fastAutofocusUri"
                  :submit-data="{ dz: 2000 }"
                  :submit-label="'Autofocus'"
                  :button-primary="false"
                  :submit-on-event="'globalFastAutofocusEvent'"
                  @taskStarted="isAutofocusing = 1"
                  @finished="isAutofocusing = 0"
                  @error="modalError"
                ></taskSubmitter>
              </div>
            </div>
          </div>
        </li>
        <li v-show="captureUri" class="uk-open">
          <a class="uk-accordion-title" href="#">Image Capture</a>
          <div class="uk-accordion-content">
            <div class="uk-grid-small uk-child-width-expand" uk-grid>
              <taskSubmitter
                v-if="captureUri"
                :submit-url="captureUri"
                :submit-data="{ resolution: 'main' }"
                :submit-label="'Low Resolution'"
                :submit-on-event="'globalCaptureEvent'"
                @response="handleCaptureResponse"
                @error="modalError"
              ></taskSubmitter>
            </div>

            <div class="uk-grid-small uk-child-width-expand" uk-grid>
              <taskSubmitter
                v-if="captureUri"
                :submit-url="captureUri"
                :submit-data="{ resolution: 'full' }"
                submit-label="Full Resolution"
                submit-on-event="globalCaptureEvent"
                @response="handleCaptureResponse"
                @error="modalError"
              ></taskSubmitter>
            </div>
          </div>
        </li>
      </ul>
    </div>
    <div v-else class="uk-text-warning">
      <p>Stage positioning is disabled since no stage is connected.</p>
      <p>
        Please check all data and power connections to your motor controller
        board.
      </p>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import taskSubmitter from "../../genericComponents/taskSubmitter";

// Export main app
export default {
  name: "PaneNavigate",

  components: {
    taskSubmitter
  },

  data: function() {
    return {
      stepXy: 200,
      stepZz: 50,
      stepSize: {
        x: 200,
        y: 200,
        z: 50
      },
      invert: {
        x: false,
        y: false,
        z: false
      },
      setPosition: null,
      isAutofocusing: 0,
      moveLock: false
    };
  },

  computed: {
    baseUri: function() {
      return this.$store.getters.baseUri;
    },
    absoluteMoveUri: function() {
      return this.thingActionUrl("stage", "move_absolute");
    },
    zeroActionUri: function() {
      return this.thingActionUrl("stage", "set_zero_position");
    },
    recentreActionUri: function() {
      return this.thingActionUrl("auto_recentre_stage", "recentre");
    },
    positionStatusUri: function() {
      return `${this.baseUri}/stage/position`;
    },
    fastAutofocusUri: function() {
      return this.thingActionUrl("autofocus", "fast_autofocus");
    },
    captureUri: function() {
      return this.thingActionUrl("camera", "capture_jpeg");
    },
    moveInImageCoordinatesUri: function() {
      return this.thingActionUrl(
        "camera_stage_mapping",
        "move_in_image_coordinates"
      );
    }
  },

  watch: {
    stepSize: {
      deep: true,
      handler() {
        this.setLocalStorageObj("navigation_stepSize", this.stepSize);
      }
    },
    invert: {
      deep: true,
      handler() {
        this.setLocalStorageObj("navigation_invert", this.invert);
      }
    }
  },

  mounted() {
    // Reload saved settings
    this.stepSize =
      this.getLocalStorageObj("navigation_stepSize") || this.stepSize;
    this.invert = this.getLocalStorageObj("navigation_invert") || this.invert;
    let self = this;
    // A global signal listener to perform a move action
    this.$root.$on("globalMoveEvent", self.move);
    // A global signal listener to perform a move action in pixels
    this.$root.$on("globalMoveInImageCoordinatesEvent", (x, y, absolute) => {
      this.moveInImageCoordinatesRequest(x, y, absolute);
    });
    // A global signal listener to perform a move in multiples of a step size
    this.$root.$on("globalMoveStepEvent", (x_steps, y_steps, z_steps) => {
      this.$root.$emit(
        "globalMoveEvent",
        x_steps * this.stepSize.x * (this.invert.x ? -1 : 1),
        y_steps * this.stepSize.y * (this.invert.y ? -1 : 1),
        z_steps * this.stepSize.z * (this.invert.z ? -1 : 1),
        false
      );
    });
    // Update the current position in text boxes
    this.updatePosition();
  },

  beforeDestroy() {
    // Remove global signal listener to perform a move action
    this.$root.$off("globalMoveEvent");
    this.$root.$off("globalMoveInImageCoordinatesEvent");
    this.$root.$off("globalMoveStepEvent");
  },

  methods: {
    timeout(ms) {
      return new Promise(resolve => setTimeout(resolve, ms));
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
          z: this.setPosition.z + z
        };
      }
      await this.timeout(1); // Wait for Vue to update the position
      await this.startMoveTask();
    },
    async startMoveTask() {
      await this.$refs.moveTaskSubmitter.startTask();
    },
    moveInImageCoordinatesRequest: function(x, y) {
      // If not movement-locked
      if (!this.moveLock) {
        // Lock move requests
        this.moveLock = true;

        if (!this.moveInImageCoordinatesUri) {
          this.modalError(
            "Moving in image coordinates is not supported - you will need to upgrade your microscope's software."
          );
        }

        // Send move request
        axios
          .post(this.moveInImageCoordinatesUri, {
            x: x, // NB the coordinates are numpy/PIL style, meaning X and Y are swapped.
            y: y
          })
          .then(() => {
            this.updatePosition(); // Update the position in text boxes
          })
          .catch(error => {
            this.modalError(error); // Let mixin handle error
          })
          .then(() => {
            this.moveLock = false; // Release the move lock
          });
      }
    },

    zeroRequest: function() {
      // Send move request
      axios
        .post(this.zeroActionUri)
        .then(() => {
          this.updatePosition(); // Update the position in text boxes
        })
        .catch(error => {
          this.modalError(error); // Let mixin handle error
        });
    },

    async updatePosition() {
      this.setPosition = await this.readThingProperty("stage", "position");
    },

    handleCaptureResponse: async function(response) {
      // Retrieve the captured image and save it
      let imageUri = response.output.href;
      if (!imageUri) {
        this.modalError("No image URI returned from capture task.");
        console.log(`Capture resulted in response ${response}`);
        return;
      }
      // To save the returned data, we make a virtual link and click it
      let imageResponse = await axios.get(imageUri, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([imageResponse.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `OFM_${new Date().toISOString()}.jpeg`);
      document.body.appendChild(link);
      link.click();
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
  width: 3em;
}
/* Chrome, Safari, Edge, Opera */
.numeric-setting-line-input::-webkit-outer-spin-button,
.numeric-setting-line-input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
.button-next-to-input {
  flex-grow: 0;
  padding-left: 5px;
  padding-right: 5px;
  vertical-align: middle;
  cursor: pointer;
}
</style>

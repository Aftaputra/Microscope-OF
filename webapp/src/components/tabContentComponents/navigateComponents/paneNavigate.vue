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

            <button
              class="uk-button uk-button-default uk-margin uk-width-1-1"
              @click="zeroRequest()"
            >
              Zero coordinates
            </button>
          </div>
        </li>

        <li class="uk-open">
          <a class="uk-accordion-title" href="#">Move-to</a>
          <div class="uk-accordion-content">
            <form @submit.prevent="handleSubmit">
              <!-- Text boxes to set and view position -->

              <div class="uk-grid-small uk-child-width-1-3" uk-grid>
                <div>
                  <label class="uk-form-label" for="form-stacked-text">x</label>
                  <div class="uk-form-controls">
                    <input
                      v-model="setPosition.x"
                      class="uk-input uk-form-small"
                      type="number"
                      name="inputPositionX"
                    />
                  </div>
                </div>

                <div>
                  <label class="uk-form-label" for="form-stacked-text">y</label>
                  <div class="uk-form-controls">
                    <input
                      v-model="setPosition.y"
                      class="uk-input uk-form-small"
                      type="number"
                      name="inputPositionY"
                    />
                  </div>
                </div>

                <div>
                  <label class="uk-form-label" for="form-stacked-text">z</label>
                  <div class="uk-form-controls">
                    <input
                      v-model="setPosition.z"
                      class="uk-input uk-form-small"
                      type="number"
                      name="inputPositionZx"
                    />
                  </div>
                </div>
              </div>

              <p>
                <button
                  type="submit"
                  class="uk-button uk-button-default uk-float-right uk-width-1-1"
                >
                  Move
                </button>
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
    moveActionUri: function() {
      return `${this.$store.getters.baseUri}/stage/move_relative`;
    },
    zeroActionUri: function() {
      return `${this.$store.getters.baseUri}/stage/zero`;
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
    // A global signal listener to perform a move action
    this.$root.$on("globalMoveEvent", (x, y, z, absolute) => {
      this.moveRequest(x, y, z, absolute);
    });
    // A global signal listener to perform a move action in pixels
    this.$root.$on("globalMoveInImageCoordinatesEvent", (x, y, absolute) => {
      this.moveInImageCoordinatesRequest(x, y, absolute);
    });
    // A global signal listener to perform a move in multiples of a step size
    this.$root.$on("globalMoveStepEvent", (x_steps, y_steps, z_steps) => {
      this.moveRequest(
        x_steps * this.stepSize.x * (this.invert.x ? -1 : 1),
        y_steps * this.stepSize.y * (this.invert.y ? -1 : 1),
        z_steps * this.stepSize.z * (this.invert.z ? -1 : 1),
        false
      );
    });
    // Update the current position in text boxes
    this.updatePosition();
    // Look for autofocus plugin
  },

  beforeDestroy() {
    // Remove global signal listener to perform a move action
    this.$root.$off("globalMoveEvent");
    this.$root.$off("globalMoveInImageCoordinatesEvent");
    this.$root.$off("globalMoveStepEvent");
  },

  methods: {
    handleSubmit: function() {
      this.moveRequest(
        this.setPosition.x,
        this.setPosition.y,
        this.setPosition.z,
        true
      );
    },

    moveRequest: function(x, y, z, absolute) {
      // If not movement-locked
      if (!this.moveLock) {
        // Lock move requests
        this.moveLock = true;
        let move_type = absolute ? "absolute" : "relative";
        // Send move request
        axios
          .post(`${this.baseUri}/stage/move_${move_type}`, {
            x: x,
            y: y,
            z: z
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

    updatePosition: function() {
      axios
        .get(this.positionStatusUri)
        .then(response => {
          this.setPosition = response.data;
        })
        .catch(error => {
          this.modalError(error); // Let mixin handle error
        });
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

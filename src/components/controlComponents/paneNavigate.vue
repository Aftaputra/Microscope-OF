<template>
  <div id="paneNavigate" class="uk-padding-small">
    <div v-if="setPosition">
      <ul uk-accordion="multiple: true; animation: false">
        <li>
          <a class="uk-accordion-title" href="#">Configure</a>
          <div class="uk-accordion-content">
            <div class="uk-child-width-1-2" uk-grid>
              <div>
                <label class="uk-form-label" for="form-stacked-text"
                  >x-y step size</label
                >
                <div class="uk-form-controls">
                  <input
                    v-model="stepXy"
                    class="uk-input uk-form-width-medium uk-form-small"
                    type="number"
                    name="inputStepXy"
                  />
                </div>
              </div>

              <div>
                <label class="uk-form-label" for="form-stacked-text"
                  >z step size</label
                >
                <div class="uk-form-controls">
                  <input
                    v-model="stepZz"
                    class="uk-input uk-form-width-medium uk-form-small"
                    type="number"
                    name="inputStepZz"
                  />
                </div>
              </div>
            </div>

            <button
              class="uk-button uk-button-default uk-form-small uk-margin uk-width-1-1"
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
                  class="uk-button uk-button-default uk-form-small uk-float-right uk-width-1-1"
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
                  :submit-label="'Fast'"
                  @taskStarted="isAutofocusing = 1"
                  @finished="isAutofocusing = 0"
                ></taskSubmitter>
              </div>

              <div v-show="!isAutofocusing || isAutofocusing == 2">
                <taskSubmitter
                  v-if="normalAutofocusUri"
                  :submit-url="normalAutofocusUri"
                  :submit-data="{ dz: [-60, -30, 0, 30, 60] }"
                  :submit-label="'Medium'"
                  @taskStarted="isAutofocusing = 2"
                  @finished="isAutofocusing = 0"
                ></taskSubmitter>
              </div>

              <div v-show="!isAutofocusing || isAutofocusing == 3">
                <taskSubmitter
                  v-if="normalAutofocusUri"
                  :submit-url="normalAutofocusUri"
                  :submit-data="{ dz: [-20, -10, 0, 10, 20] }"
                  :submit-label="'Fine'"
                  @taskStarted="isAutofocusing = 3"
                  @finished="isAutofocusing = 0"
                ></taskSubmitter>
              </div>
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
import taskSubmitter from "../genericComponents/taskSubmitter";

// Key Codes
const keyCodes = {
  pgup: 33,
  pgdn: 34,
  left: 37,
  up: 38,
  right: 39,
  down: 40,
  enter: 13,
  esc: 27
};

// Export main app
export default {
  name: "PaneNavigate",

  components: {
    taskSubmitter
  },

  data: function() {
    return {
      keysDown: {},
      stepXy: 200,
      stepZz: 50,
      setPosition: null,
      isAutofocusing: 0,
      moveLock: false,
      fastAutofocusUri: null,
      normalAutofocusUri: null,
      moveInImageCoordinatesUri: null
    };
  },

  computed: {
    moveActionUri: function() {
      return `${this.$store.getters.baseUri}/api/v2/actions/stage/move`;
    },
    zeroActionUri: function() {
      return `${this.$store.getters.baseUri}/api/v2/actions/stage/zero`;
    },
    positionStatusUri: function() {
      return `${this.$store.getters.baseUri}/api/v2/instrument/state/stage/position`;
    },
    pluginsUri: function() {
      return `${this.$store.getters.baseUri}/api/v2/extensions`;
    }
  },

  created: function() {
    window.addEventListener("keydown", this.keyDownMonitor);
    window.addEventListener("keyup", this.keyUpMonitor);
    window.addEventListener("wheel", this.wheelMonitor);
  },

  mounted() {
    // A global signal listener to perform a move action
    this.$root.$on("globalMoveEvent", (x, y, z, absolute) => {
      this.moveRequest(x, y, z, absolute);
    });
    // A global signal listener to perform a move action
    this.$root.$on("globalMoveInImageCoordinatesEvent", (x, y, absolute) => {
      this.moveInImageCoordinatesRequest(x, y, absolute);
    });
    // Update the current position in text boxes
    this.updatePosition();
    // Look for autofocus plugin
    this.updateAutofocusUri();
    this.updateMoveInImageCoordinatesUri();
  },

  beforeDestroy() {
    // Remove global signal listener to perform a move action
    this.$root.$off("globalMoveEvent");
  },

  destroyed: function() {
    window.removeEventListener("keydown", this.keyDownMonitor);
    window.removeEventListener("keyup", this.keyUpMonitor);
    window.removeEventListener("wheel", this.wheelMonitor);
  },

  methods: {
    // Handle global mouse wheel events to be associated with navigation
    wheelMonitor: function(event) {
      // Only capture scroll if the event target's parent contains the "scrollTarget" class
      if (
        event.target.parentNode.classList.contains("scrollTarget") ||
        event.target.classList.contains("scrollTarget")
      ) {
        var z_rel = (event.deltaY / 100) * this.stepZz;
        this.moveRequest(0, 0, z_rel, false);
      }
    },

    // Handle global key press events to be associated with navigation
    keyDownMonitor: function(event) {
      this.keysDown[event.keyCode] = true; //Add key to array

      // Convert keyCode dict into a list of key codes
      var keyCodeList = Object.keys(keyCodes).map(function(key) {
        return keyCodes[key];
      });

      if (
        !(event.target instanceof HTMLInputElement) &&
        !event.target.classList.contains("lightbox-link") &&
        keyCodeList.includes(event.keyCode)
      ) {
        //console.log(this.keysDown)
        // Calculate movement array
        var x_rel = 0;
        var y_rel = 0;
        var z_rel = 0;
        if (keyCodes.left in this.keysDown) {
          x_rel = x_rel + this.stepXy;
        }
        if (keyCodes.right in this.keysDown) {
          x_rel = x_rel - this.stepXy;
        }
        if (keyCodes.up in this.keysDown) {
          y_rel = y_rel + this.stepXy;
        }
        if (keyCodes.down in this.keysDown) {
          y_rel = y_rel - this.stepXy;
        }
        if (keyCodes.pgup in this.keysDown) {
          z_rel = z_rel - this.stepZz;
        }
        if (keyCodes.pgdn in this.keysDown) {
          z_rel = z_rel + this.stepZz;
        }

        // Make a position request
        this.moveRequest(x_rel, y_rel, z_rel, false);
      }
    },

    keyUpMonitor: function(event) {
      delete this.keysDown[event.keyCode]; //Remove key from array
    },

    handleSubmit: function() {
      this.moveRequest(
        this.setPosition.x,
        this.setPosition.y,
        this.setPosition.z,
        true
      );
    },

    moveRequest: function(x, y, z, absolute) {
      console.log(`Sending move request of ${x}, ${y}, ${z}`);
      // If not movement-locked
      if (!this.moveLock) {
        // Lock move requests
        this.moveLock = true;

        // Send move request
        axios
          .post(this.moveActionUri, {
            x: x,
            y: y,
            z: z,
            absolute: absolute
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
      console.log(`Sending move request in image coordinates: ${x}, ${y}`);
      // If not movement-locked
      if (!this.moveLock) {
        // Lock move requests
        this.moveLock = true;

        if (!this.moveInImageCoordinatesUri){
          this.modalError("Moving in image coordinates is not supported - you will need to upgrade your microscope's software.");
        }

        // Send move request
        axios
          .post(this.moveInImageCoordinatesUri, {
            x: y, // NB the coordinates are numpy/PIL style, meaning X and Y are swapped.
            y: x,
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

    updateAutofocusUri: function() {
      axios
        .get(this.pluginsUri) // Get a list of plugins
        .then(response => {
          var plugins = response.data;
          var foundExtension = plugins.find(
            e => e.title === "org.openflexure.autofocus"
          );
          // if ScanPlugin is enabled
          if (foundExtension) {
            // Get plugin action link
            this.fastAutofocusUri = foundExtension.links.fast_autofocus.href;
            this.normalAutofocusUri = foundExtension.links.autofocus.href;
          }
        })
        .catch(error => {
          this.modalError(error); // Let mixin handle error
        });
    },

    updateMoveInImageCoordinatesUri: function() {
      axios
        .get(this.pluginsUri) // Get a list of plugins
        .then(response => {
          var plugins = response.data;
          var foundExtension = plugins.find(
            e => e.title === "org.openflexure.camera_stage_mapping"
          );
          if (foundExtension) {
            // Get plugin action link
            this.moveInImageCoordinatesUri = foundExtension.links.move_in_image_coordinates.href;
          }
        })
        .catch(error => {
          this.modalError(error); // Let mixin handle error
        });
    }
  }
};
</script>

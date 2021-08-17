<template>
  <div id="stageSettings" class="uk-width-large">
    <div v-if="stageType === 'MissingStage'" class="uk-text-danger">
      <b>No stage connected</b>
    </div>
    <div v-else>
      <h3>Stage settings</h3>
      <form @submit.prevent="setStageType">
        <div class="uk-margin-small-bottom">
          <h4>Stage geometry</h4>
          <select v-model="stageType" class="uk-select uk-margin-small-top">
            <option value="SangaStage">SangaStage (Standard)</option>
            <option value="SangaDeltaStage"> SangaStage (Delta)</option>
          </select>

          <button
            type="submit"
            class="uk-button uk-button-primary uk-margin-small uk-width-1-1"
          >
            Change stage geometry
          </button>
        </div>
      </form>

      <form @submit.prevent="applySettingsRequest">
        <div class="uk-margin-small-bottom">
          <h4>Backlash compensation</h4>
          <p class="uk-margin-remove">
            Backlash compentation causes movements to overshoot by that number
            of motor steps, reducing the effect of mechanical backlash.
          </p>
          <div
            class="uk-grid-small uk-child-width-1-3 uk-margin-small-bottom"
            uk-grid
          >
            <div>
              <label class="uk-form-label" for="form-stacked-text">x</label>
              <div class="uk-form-controls">
                <input
                  v-model="backlash.x"
                  class="uk-input uk-form-small"
                  type="number"
                />
              </div>
            </div>

            <div>
              <label class="uk-form-label" for="form-stacked-text">y</label>
              <div class="uk-form-controls">
                <input
                  v-model="backlash.y"
                  class="uk-input uk-form-small"
                  type="number"
                />
              </div>
            </div>

            <div>
              <label class="uk-form-label" for="form-stacked-text">z</label>
              <div class="uk-form-controls">
                <input
                  v-model="backlash.z"
                  class="uk-input uk-form-small"
                  type="number"
                />
              </div>
            </div>
          </div>

          <h4>Settle time</h4>
          <div v-if="settle_time !== undefined">
            <p class="uk-margin-small-bottom">
              When moving or scanning, captures will be delayed by the settle
              time (in seconds) to reduce motion blur.
            </p>
            <div class="uk-form-controls">
              <input
                v-model="settle_time"
                class="uk-input uk-form-small"
                type="number"
                step="0.1"
              />
            </div>
          </div>

          <button
            type="submit"
            class="uk-button uk-button-primary uk-margin-small uk-width-1-1"
          >
            Apply Settings
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script>
import axios from "axios";

export default {
  name: "StageSettings",

  components: {},

  data: function() {
    return {
      stageType: "MissingStage",
      backlash: {
        x: undefined,
        y: undefined,
        z: undefined
      },
      settle_time: undefined
    };
  },

  computed: {
    settingsUri: function() {
      return `${this.$store.getters.baseUri}/api/v2/instrument/settings`;
    },
    stageTypeUri: function() {
      return `${this.$store.getters.baseUri}/api/v2/instrument/stage/type`;
    }
  },

  mounted() {
    this.getStageType();
    this.updateSettings();
  },

  methods: {
    updateSettings: function() {
      axios
        .get(this.settingsUri)
        .then(response => {
          const stageSettings = response.data.stage;
          this.backlash.x = stageSettings.backlash.x;
          this.backlash.y = stageSettings.backlash.y;
          this.backlash.z = stageSettings.backlash.z;
          this.settle_time = stageSettings.settle_time;
        })
        .catch(error => {
          this.modalError(error); // Let mixin handle error
        });
    },
    applySettingsRequest: function() {
      var payload = {
        stage: {
          backlash: this.backlash
        }
      };
      // Send request to update settings
      axios
        .put(this.settingsUri, payload)
        .then(() => {
          // Update local settings
          this.updateSettings();
          this.modalNotify("Stage settings applied.");
        })
        .catch(error => {
          this.modalError(error); // Let mixin handle error
        });
    },
    getStageType: function() {
      axios
        .get(this.stageTypeUri)
        .then(response => {
          this.stageType = response.data;
        })
        .catch(error => {
          this.modalError(error);
        });
    },
    setStageType: function() {
      axios
        .put(this.stageTypeUri, this.stageType, {
          headers: {
            "Content-Type": "application/json"
          }
        })
        .then(response => {
          this.stageType = response.data;

          this.modalNotify("Stage geometry changed.");
        })
        .catch(error => {
          this.modalError(error);
        });
    }
  }
};
</script>

<style lang="less"></style>

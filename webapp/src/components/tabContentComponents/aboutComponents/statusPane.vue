<template>
  <div class="host-input">
    <div v-if="$store.state.available">
      <div>
        <div class="uk-margin-small-bottom">
          <b>API origin:</b>
          <br />
          {{ $store.state.origin }}
        </div>
      </div>

      <hr />

      <div>
        <b>Server version:</b> <br />
        TODO
      </div>

      <hr />

      <div class="uk-margin-small-bottom">
        <b>Camera:</b>
        <br />
        <div v-if="'camera' in things">
          {{ things.camera.title }}
        </div>
        <div v-else class="uk-text-danger"><b>No camera configured</b></div>
      </div>
      <div>
        <b>Stage:</b>
        <br />
        <div v-if="'stage' in things">
          {{ things.stage.title }}
        </div>
        <div v-else class="uk-text-danger"><b>No stage configured</b></div>
      </div>

      <hr />

      <div class="uk-grid-small uk-child-width-1-2" uk-grid>
        <div>
          <button
            v-show="'shutdown' in systemControlActions"
            class="uk-button uk-button-danger uk-float-right uk-margin uk-margin-remove-top uk-width-1-1"
            @click="shutdownRequest"
          >
            Shutdown
          </button>
        </div>

        <div>
          <button
            v-show="'reboot' in systemControlActions"
            class="uk-button uk-button-danger uk-float-right uk-margin uk-margin-remove-top uk-width-1-1"
            @click="rebootRequest"
          >
            Restart
          </button>
        </div>
      </div>
    </div>
    <div v-else-if="$store.state.waiting">
      Loading...
    </div>
    <div v-else-if="$store.state.error">
      <b>Error:</b> {{ $store.state.error }}
    </div>
    <div v-else>No active connection</div>
  </div>
</template>

<script>
import axios from "axios";

export default {
  name: "StatusPane",

  components: {},

  data: function() {
    return {
      things: {},
      systemControlActions: {}
    };
  },

  computed: {
    baseUri: function() {
      return `${this.$store.getters.baseUri}/`;
    }
  },

  mounted: function() {
    // Watch for host 'ready', then update configuration
    this.updateConfiguration();
    this.updateActions();
  },

  methods: {
    updateConfiguration: async function() {
      console.log("Showing the configuration is not yet fully implemented");
      // Retrieve TDs for camera and stage
      let things = {};
      for (let thing of ["camera", "stage"]) {
        try {
          let response = await axios.get(this.baseUri + thing); // Get Thing Description
          things[thing] = response.data;
        } catch (error) {
          console.log(thing + " was missing", error);
        }
      }
      this.things = things; // We must set this.things in order to trigger the UI update
    },
    updateActions: async function() {
      try {
        let response = await axios.get(this.baseUri + "system_control"); // Get Thing Description
        this.systemControlActions = response.data.actions;
      } catch (error) {
        console.log(
          "system control was missing - shutdown/restart buttons will not appear",
          error
        );
      }
    },
    shutdownRequest: function() {
      this.modalConfirm("Shut down microscope?").then(
        () => {
          this.$store.commit("resetState");
          // Post and silence errors
          axios.post(this.baseUri + "system_control/shutdown").catch(() => {});
        },
        () => {}
      );
    },
    rebootRequest: function() {
      this.modalConfirm("Restart microscope?").then(
        () => {
          this.$store.commit("resetState");
          // Post and silence errors
          axios.post(this.baseUri + "system_control/restart").catch(() => {});
        },
        () => {}
      );
    }
  }
};
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped lang="less"></style>

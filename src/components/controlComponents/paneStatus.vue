<template>
  <div class="host-input">
    <div v-if="status && $store.getters.ready">
      <div>
        <div class="uk-margin-small-bottom">
          <b>Host:</b>
          <br />
          {{ $store.state.host }}
        </div>
      </div>

      <hr />

      <div v-if="settings">
        <b>Device name:</b> <br />
        {{ settings.name }}
      </div>
      <div>
        <b>Server version:</b> <br />
        {{ status.version }}
      </div>

      <hr />

      <div class="uk-margin-small-bottom">
        <b>Camera:</b>
        <br />
        <div v-if="status.camera.board">
          {{ status.camera.board }}
        </div>
        <div v-else class="uk-text-danger"><b>No camera connected</b></div>
      </div>
      <div>
        <b>Stage:</b>
        <br />
        <div v-if="status.stage.board">
          {{ status.stage.board }}
        </div>
        <div v-else class="uk-text-danger"><b>No stage connected</b></div>
      </div>

      <hr />

      <div class="uk-grid-small uk-child-width-1-2" uk-grid>
        <div>
          <button
            v-if="'shutdown' in systemActionLinks"
            class="uk-button uk-button-danger uk-form-small uk-float-right uk-margin uk-margin-remove-top uk-width-1-1"
            @click="shutdownRequest"
          >
            Shutdown
          </button>
        </div>

        <div>
          <button
            v-if="'reboot' in systemActionLinks"
            class="uk-button uk-button-danger uk-form-small uk-float-right uk-margin uk-margin-remove-top uk-width-1-1"
            @click="rebootRequest"
          >
            Restart
          </button>
        </div>
      </div>
    </div>
    <div v-else-if="$store.state.waiting">
      <progressBar></progressBar>
    </div>
    <div v-else-if="$store.state.error">
      <b>Error:</b> {{ $store.state.error }}
    </div>
    <div v-else>No active connection</div>
  </div>
</template>

<script>
import axios from "axios";
import progressBar from "../genericComponents/progressBar";

export default {
  name: "PaneStatus",

  components: {
    progressBar
  },

  data: function() {
    return {
      status: null,
      settings: null,
      systemActionLinks: {}
    };
  },

  computed: {
    settingsUri: function() {
      return `${this.$store.getters.baseUri}/api/v2/settings`;
    },
    statusUri: function() {
      return `${this.$store.getters.baseUri}/api/v2/status`;
    },
    actionsUri: function() {
      return `${this.$store.getters.baseUri}/api/v2/actions`;
    }
  },

  created: function() {
    // Watch for host 'ready', then update status
    this.$store.watch(
      (state, getters) => {
        return getters.ready;
      },
      () => {
        this.updateStatus();
        this.updateSettings();
        this.updateSystemActions();
      }
    );
  },

  methods: {
    updateStatus: function() {
      axios
        .get(this.statusUri)
        .then(response => {
          this.status = response.data;
        })
        .catch(error => {
          this.modalError(error); // Let mixin handle error
        });
    },
    updateSettings: function() {
      axios
        .get(this.settingsUri)
        .then(response => {
          this.settings = response.data;
        })
        .catch(error => {
          this.modalError(error); // Let mixin handle error
        });
    },
    updateSystemActions: function() {
      axios
        .get(this.actionsUri)
        .then(response => {
          if ("reboot" in response.data) {
            this.systemActionLinks.reboot =
              response.data.reboot.links.self.href;
          } else {
            delete this.systemActionLinks.reboot;
          }
          if ("shutdown" in response.data) {
            this.systemActionLinks.shutdown =
              response.data.shutdown.links.self.href;
          } else {
            delete this.systemActionLinks.shutdown;
          }
        })
        .catch(error => {
          this.modalError(error); // Let mixin handle error
        });
    },
    shutdownRequest: function() {
      this.modalConfirm("Shut down microscope?").then(
        () => {
          if ("shutdown" in this.systemActionLinks) {
            axios
              .post(this.systemActionLinks.shutdown)
              .then(() => {
                this.$store.commit("resetState");
              })
              .catch(error => {
                this.modalError(error); // Let mixin handle error
              });
          }
        },
        () => {}
      );
    },
    rebootRequest: function() {
      this.modalConfirm("Restart microscope?").then(
        () => {
          if ("reboot" in this.systemActionLinks) {
            axios
              .post(this.systemActionLinks.reboot)
              .then(() => {
                this.$store.commit("resetState");
              })
              .catch(error => {
                this.modalError(error); // Let mixin handle error
              });
          }
        },
        () => {}
      );
    }
  }
};
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped lang="less"></style>

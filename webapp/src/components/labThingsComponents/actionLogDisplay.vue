<template>
  <div class="log-wrapper" @mouseenter="onMouseEnter" @mouseleave="onMouseLeave">
    <div ref="logContainer" class="log-container uk-margin-left uk-margin-right uk-margin">
      <div v-if="log">
        <div v-for="(item, index) in log" :key="`log_entry_${index}`">
          {{ item.message }}
        </div>
      </div>
      <div v-if="taskStatus == 'error'" class="uk-alert uk-alert-danger">
        <p><b>The task failed due to an error:</b></p>
        <p>{{ errorMessage }}</p>
      </div>
      <div v-if="taskStatus == 'cancelled'" class="uk-alert uk-alert-warning">
        The task was cancelled.
      </div>
      <div v-if="taskStatus == 'completed'" class="uk-alert uk-alert-success">
        The task completed successfully.
      </div>

      <!-- Paused banner outside scroll container, positioned relative to wrapper -->
      <div v-if="userIsHovering" class="paused-banner">Auto-scroll paused</div>
    </div>
  </div>
</template>

<script>
export default {
  name: "ActionLogDisplay",

  props: {
    taskStatus: {
      type: String,
      required: true,
    },
    log: {
      type: Array,
      required: true,
    },
  },

  data() {
    return {
      userIsHovering: false,
    };
  },

  computed: {
    errorMessage() {
      let logLength = this.log.length;
      var defaultMessage = "Unexpected error, please check the logs";
      if (logLength == 0) {
        return defaultMessage;
      }
      // Cannot use .at until we update OpenFlexure Connect
      if (this.log[logLength - 1].levelname != "ERROR") {
        return defaultMessage;
      }
      return this.log[logLength - 1].message || defaultMessage;
    },
  },

  watch: {
    log: {
      handler() {
        this.scrollToBottom();
      },
      deep: true,
    },
    taskStatus: {
      handler() {
        this.scrollToBottom();
      },
    },
  },

  methods: {
    onMouseEnter() {
      this.userIsHovering = true;
    },
    onMouseLeave() {
      this.userIsHovering = false;
    },

    scrollToBottom() {
      /*Scroll to bottom of log unless the user is hovering over the log.*/
      this.$nextTick(() => {
        if (this.userIsHovering) return;

        const viewer = this.$refs.logContainer;
        viewer.scrollTop = viewer.scrollHeight;
      });
    },
  },
};
</script>

<style scoped>
.log-wrapper {
  position: relative;
  height: 200px;
  overflow: hidden;
  margin-bottom: 1em;
  margin-top: 1em;
}

.log-container {
  height: 100%;
  overflow-y: auto;
  overflow-x: auto;
  background-color: white;
  color: black;
  padding: 0.5em;
  border: 1px solid black;
  box-sizing: border-box;
}

/* Floating banner fixed at top-right of wrapper, not affected by scroll */
.paused-banner {
  position: absolute;
  top: 8px;
  right: 40px;
  color: black;
  font-weight: bold;
  padding: 4px;
  border-radius: 4px;
  z-index: 10;
  font-size: 0.85em;
  pointer-events: none;
  box-shadow: 0 0 4px rgba(0, 0, 0, 0.2);
  background-color: white;
}
</style>

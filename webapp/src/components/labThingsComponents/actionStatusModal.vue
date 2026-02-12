<template>
  <div ref="modal" class="" uk-modal="bg-close: false; esc-close: false; stack: true;">
    <div id="status-modal" class="uk-modal-dialog uk-modal-body uk-margin-auto-vertical">
      <h2>{{ title }}</h2>
      <action-log-display :log="log" :task-status="taskStatus" />
      <div id="progress-and-cancel-row">
        <div class="stretchy">
          <action-progress-bar :progress="progress" :task-status="taskStatus" />
        </div>

        <button
          v-if="canTerminate && taskRunning"
          type="button"
          class="uk-button uk-button-danger not-stretchy"
          @click="$emit('terminateTask')"
        >
          Cancel
        </button>
        <button v-if="!taskStarted" type="button" class="uk-button not-stretchy" @click="hide">
          Close
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import UIkit from "uikit";
import ActionProgressBar from "./actionProgressBar.vue";
import ActionLogDisplay from "./actionLogDisplay.vue";
// vue3 migration
import { markRaw } from "vue";
import { eventBus } from "../../eventBus.js";

export default {
  name: "ActionStatusModal",
  components: { 
    ActionProgressBar: markRaw(ActionProgressBar),
    ActionLogDisplay: markRaw(ActionLogDisplay)
  },
  props: {
    title: {
      type: String,
      required: true,
    },
    log: {
      type: Array,
      required: true,
    },
    progress: {
      type: Number,
      required: false,
      default: null,
    },
    canTerminate: {
      type: Boolean,
      required: true,
    },
    taskRunning: {
      type: Boolean,
      required: true,
    },
    taskStarted: {
      type: Boolean,
      required: true,
    },
    taskStatus: {
      type: String,
      required: true,
    },
  },

  methods: {
    show() {
      UIkit.modal(this.$refs.modal).show();
    },
    hide() {
      UIkit.modal(this.$refs.modal).hide();
      eventBus.emit("modalClosed");
    },
  },
};
</script>
<style lang="less" scoped>
@import "../../assets/less/theme.less";

#progress-and-cancel-row {
  display: flex;
  flex-flow: row wrap;
  justify-content: flex-start;
  align-content: stretch;
  align-items: center;
  width: 100%;
}

#progress-and-cancel-row .stretchy {
  flex-grow: 1;
  margin-left: 5px;
  margin-right: 5px;
}
#progress-and-cancel-row .not-stretchy {
  flex-grow: 0;
  margin-left: 5px;
  margin-right: 5px;
}

#status-modal .log-container {
  height: 10em;
}
</style>

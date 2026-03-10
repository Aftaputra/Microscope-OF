<template>
  <div ref="actionTab" uk-grid class="uk-height-1-1 uk-margin-remove uk-padding-remove">
    <div class="control-component uk-padding-small">
      <div v-if="!taskStarted" class="uk-padding-small">
        <slot name="controls"></slot>
      </div>
      <div v-if="taskStarted">
        <h2 v-if="taskInfoTitle" style="text-align: center">{{ taskInfoTitle }}</h2>
        <mini-stream-display v-if="taskInfoStream" />
        <action-log-display id="log-display" :log="log" :task-status="taskStatus" />
        <action-button
          v-if="taskRunning"
          :thing="thing"
          :action="action"
          :force-id="taskId"
          :force-url="taskUrl"
          submit-label=""
          :can-terminate="true"
          @completed="$emit('completed')"
          @update:task-status="taskStatus = $event"
          @update:progress="progress = $event"
          @update:log="log = $event"
        />
        <button
          v-if="!taskRunning"
          type="button"
          class="uk-button uk-width-1-1 uk-position-relative"
          @click="closeTask"
        >
          Close
        </button>
        <slot name="task-info"></slot>
      </div>
    </div>
    <div class="main-view uk-width-expand uk-height-1-1">
      <slot></slot>
    </div>
  </div>
</template>

<script>
import actionLogDisplay from "../labThingsComponents/actionLogDisplay.vue";
import MiniStreamDisplay from "../genericComponents/miniStreamDisplay.vue";
import ActionButton from "../labThingsComponents/actionButton.vue";
import { useIntersectionObserver } from "@vueuse/core";

export default {
  name: "ActionTab",

  components: {
    actionLogDisplay,
    MiniStreamDisplay,
    ActionButton,
  },

  props: {
    action: {
      type: String,
      required: true,
    },
    thing: {
      type: String,
      required: true,
    },
    taskId: {
      type: [String, null],
      required: true,
    },
    taskUrl: {
      type: [String, null],
      required: true,
    },
    taskInfoTitle: {
      type: String,
      required: false,
      default: null,
    },
    taskInfoStream: {
      type: Boolean,
      required: false,
      default: false,
    },
  },

  emits: ["closeTask", "completed", "actionStartedExternally"],

  data() {
    return {
      taskStatus: "pending",
      progress: null,
      log: [],
      pollTimer: null,
    };
  },

  computed: {
    taskStarted() {
      return this.taskId && this.taskUrl;
    },
    taskRunning() {
      return (this.taskStatus == "running") | (this.taskStatus == "pending");
    },
  },

  mounted() {
    useIntersectionObserver(
      this.$refs.actionTab,
      ([{ isIntersecting }]) => {
        this.visibilityChanged(isIntersecting);
      },
      {
        threshold: 0.0, // Adjust as needed
      },
    );
  },

  methods: {
    /**
     * Reset the data needed for actions to be polled.
     */
    resetData() {
      this.taskStatus = "pending";
      this.log = [];
    },
    closeTask() {
      // Reset task status to pending so that it is re-read next time an action starts.
      this.resetData();
      this.$emit("closeTask");
    },
    visibilityChanged(isVisible) {
      this.isVisible = isVisible;

      if (this.isVisible) {
        this.startTimer();
      } else {
        this.stopTimer();
      }
    },
    startTimer() {
      if (this.pollTimer) return;

      this.pollTimer = setInterval(() => {
        this.checkIfStartedExternally();
      }, 1000);
    },
    stopTimer() {
      if (!this.pollTimer) return;

      clearInterval(this.pollTimer);
      this.pollTimer = null;
    },
    async checkIfStartedExternally() {
      if (!this.taskStarted | !this.taskRunning) {
        const ongoingTask = await this.getOngingAction(this.thing, this.action);
        if (ongoingTask) {
          this.resetData();
          const taskUrl = ongoingTask.links.find((t) => t.rel == "self").href;
          this.$emit("actionStartedExternally", ongoingTask.id, taskUrl);
        }
      }
    },
  },
};
</script>

<style scoped>
.control-component {
  width: 33%;
}
#log-display {
  height: 20em;
}
</style>

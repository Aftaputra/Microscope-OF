<template>
  <div class="uk-margin-remove uk-padding-remove">
    <button
      ref="actionButton"
      type="button"
      :disabled="buttonDisabled"
      class="uk-button uk-width-1-1 uk-position-relative"
      :class="buttonClasses"
      @click="handleClick"
    >
      <action-progress-bar :progress="progress" :task-status="taskStatus" :in-button="true" />
      {{ buttonLabel }}
    </button>

    <action-status-modal
      ref="statusModal"
      :title="submitLabel"
      :log="log"
      :progress="progress"
      :can-terminate="canTerminate"
      :task-running="taskRunning"
      :task-started="taskStarted"
      :task-status="taskStatus"
      @terminateTask="terminateTask"
    />
  </div>
</template>

<script>
import ActionProgressBar from "./actionProgressBar.vue";
import ActionStatusModal from "./actionStatusModal.vue";
//vue3 migration 
import { eventBus } from "../../eventBus.js";
import { useIntersectionObserver } from "@vueuse/core";


export default {
  name: "ActionButton",

  emits: [
    'update:progress',
    'update:taskStarted', 
    'update:taskRunning',
    'update:log',
    'update:taskStatus',
    'submit',
    'taskStarted',
    'taskRunning',
    'response',
    'completed',
    'cancelled',
    'finished',
    'error'
  ],

  components: { 
    ActionProgressBar,
    ActionStatusModal
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
    submitData: {
      type: [Object, Array],
      required: false,
      default: () => ({}),
    },
    pollInterval: {
      type: Number,
      required: false,
      default: 1,
    },
    submitLabel: {
      type: String,
      required: false,
      default: "Submit",
    },
    canTerminate: {
      type: Boolean,
      required: false,
      default: true,
    },
    requiresConfirmation: {
      type: Boolean,
      required: false,
      default: false,
    },
    confirmationMessage: {
      type: String,
      required: false,
      default: "Start task?",
    },
    buttonPrimary: {
      type: Boolean,
      required: false,
      default: true,
    },
    submitOnEvent: {
      type: String,
      required: false,
      default: null,
    },
    modalProgress: {
      type: Boolean,
      required: false,
      default: false,
    },
    isDisabled: {
      type: Boolean,
      required: false,
      default: false,
    },
  },

  data: function () {
    return {
      taskUrl: null,
      progress: null,
      taskStarted: false,
      taskRunning: false,
      log: [],
      taskStatus: "",
    };
  },

  computed: {
    buttonDisabled() {
      return this.isDisabled || (this.taskRunning && !this.canTerminate);
    },
    buttonLabel() {
      return this.taskRunning && this.canTerminate ? "Cancel" : this.submitLabel;
    },
    buttonClasses() {
      const classes = [];
      if (this.buttonDisabled) {
        classes.push("uk-button-disabled");
      }
      if (this.taskRunning && this.canTerminate) {
        classes.push("uk-button-danger");
      } else if (this.buttonPrimary) {
        classes.push("uk-button-primary");
      } else {
        classes.push("uk-button-default");
      }
      return classes.join(" ");
    },
  },

  watch: {
    progress: {
      handler(newval) {
        this.$emit("update:progress", newval);
      },
    },
    taskStarted: {
      handler(newval) {
        this.$emit("update:taskStarted", newval);
      },
    },
    taskRunning: {
      handler(newval) {
        this.$emit("update:taskRunning", newval);
      },
    },
    log: {
      handler(newval) {
        this.$emit("update:log", newval);
      },
      deep: true
    },
    taskStatus: {
      handler(newval) {
        this.$emit("update:taskStatus", newval);
      },
    }
},

  mounted() {
    useIntersectionObserver(
      this.$refs.actionButton,
      ([{ isIntersecting }]) => {
        this.visibilityChanged(isIntersecting);
      },
      {
        threshold: 0.0, // Adjust as needed
      },
    );

    // Check for already running tasks
    if (this.taskStarted != true) {
      this.checkExistingTasks();
    }
    // A global signal listener to perform the action
    if (this.submitOnEvent) {
      eventBus.on(this.submitOnEvent, () => {
        if (this.isDisabled) return;
        // Bootstrap task if button is not disabled.
        this.bootstrapTask();
      });
    }
  },

  beforeUnmount() {
    if (this.submitOnEvent) {
      eventBus.off(this.submitOnEvent);
    }
  },

  methods: {
    handleClick() {
      if (this.taskStarted) {
        this.terminateTask();
      } else {
        this.bootstrapTask();
      }
    },
    visibilityChanged(isVisible) {
      if (isVisible && this.taskStarted != true) {
        this.checkExistingTasks();
      }
    },

    /* Check if an existing task had already started when this mounts.
     *
     * This is called on mounted.
     *
     * It will emit taskStarted if it finds an ongoing task to allow parent components
     * to act as expected if the task is started. It will then poll the action.
     *
     */
    async checkExistingTasks() {
      let response = await this.findOngoingActions(this.thing, this.action);
      // Exit if response is null, due to an error.
      if (response == null) return;
      // Check for a task that is ongoing.
      // We can't handle multiple tasks ongoing, so this picks the first.
      const ongoingTask = response.data.find((t) => ["pending", "running"].includes(t.status));
      if (ongoingTask) {
        // There is a started task
        this.taskStarted = true;
        this.$emit("taskStarted");
        // Find its URL
        const taskUrl = ongoingTask.links.find((t) => t.rel == "self").href;
        this.startPollingTask(ongoingTask.id, taskUrl);
      }
    },

    bootstrapTask: function () {
      // Starts the process of creating a new Actiont ask
      if (this.requiresConfirmation) {
        this.modalConfirm(this.confirmationMessage).then(
          () => {
            this.startTask();
          },
          () => {},
        );
      } else {
        this.startTask();
      }
    },

    async startTask() {
      // Starts a new Action task
      console.log("Starting task with data:", this.submitData);
      this.$emit("submit", this.submitData);
      // Send a request to start a task
      this.taskStarted = true;
      this.$emit("taskStarted");
      let response;
      try {
        response = await this.invokeAction(
          this.thing,
          this.action,
          this.submitData,
          false, // Stop invokeAction handling the error.
        );
      } catch (error) {
        this.$emit("error", error);
        this.onTaskEnd();
        return;
      }
      if (this.modalProgress) {
        this.$refs.statusModal.show();
      }
      // This just starts the polling. No need to await it.
      this.startPollingTask(response.data.id, response.data.href);
    },

    async startPollingTask(taskId, taskUrl) {
      // Return if taskRunning already set.
      if (this.taskRunning) return;
      // Starts polling an existing Action task
      this.taskUrl = taskUrl;
      // Start the store polling TaskId for success
      this.taskRunning = true;
      this.$emit("taskRunning", taskId);
      this.pollUntilComplete(
        taskUrl,
        this.onPollingResponse,
        this.onTaskEnd, // Method to run after task (even if error)
        500, // Interval
      );
    },

    onTaskEnd: function (response) {
      if (response) {
        this.taskStatus = response.data.status;
        this.log = response.data.log;
        if (response.data.status == "completed") {
          this.$emit("response", response.data);
          this.$emit("completed", response.data.output);
        } else if (response.data.status == "cancelled") {
          this.$emit("cancelled", response.data);
          this.modalNotify(`The action '${this.submitLabel}' was cancelled.`);
        }
      }
      this.taskUrl = null;
      this.taskRunning = false;
      this.taskStarted = false;
      this.$emit("finished");
    },

    onPollingResponse(response) {
      // While the task is still running, we update progress/log,
      // and schedule another poll
      var result = response.data.status;
      this.taskStatus = result;
      this.progress = response.data.progress;
      this.log = response.data.log;
    },

    terminateTask: function () {
      if (this.taskUrl) {
        this.terminateAction(this.taskUrl);
      }
    },
  },
};
</script>

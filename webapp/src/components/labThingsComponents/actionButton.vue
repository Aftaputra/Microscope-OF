<template>
  <div v-observe-visibility="visibilityChanged" class="uk-margin-remove uk-padding-remove">
    <div v-if="taskStarted" ref="isPollingElement">
      <action-progress-bar
        v-if="taskStarted && hideOnRun"
        :progress="progress"
        :task-status="taskStatus"
      />
      <!-- hideOnRun selects if the button hides, don't show progress bar if button doesn't hide. -->
      <button
        v-if="canTerminate && taskRunning"
        type="button"
        class="uk-button uk-button-danger uk-margin-remove uk-float-right uk-width-1-1"
        @click="terminateTask"
      >
        Cancel
      </button>
    </div>

    <div>
      <button
        type="button"
        :disabled="isDisabled"
        :hidden="taskStarted && hideOnRun"
        class="uk-button uk-width-1-1"
        :class="[
          isDisabled ? 'uk-button-disabled' : '',
          buttonPrimary ? 'uk-button-primary' : 'uk-button-default',
        ]"
        @click="bootstrapTask"
      >
        {{ submitLabel }}
      </button>
    </div>
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

export default {
  name: "ActionButton",
  components: { ActionProgressBar, ActionStatusModal },

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
    hideOnRun: {
      type: Boolean,
      required: false,
      default: true,
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
    submitUrl() {
      return this.thingActionUrl(this.thing, this.action);
    },
  },

  watch: {
    progress(newval) {
      this.$emit("update:progress", newval);
    },
    taskStarted(newval) {
      this.$emit("update:taskStarted", newval);
    },
    taskRunning(newval) {
      this.$emit("update:taskRunning", newval);
    },
    log(newval) {
      this.$emit("update:log", newval);
    },
    taskStatus(newval) {
      this.$emit("update:taskStatus", newval);
    },
  },

  mounted() {
    //Define .from_index() as a custom function, working similar to .at()
    //For backwards compatibility, not using in-built .at() until updates to Connect
    function from_index(n) {
      // ToInteger() abstract op
      n = Math.trunc(n) || 0;
      // Allow negative indexing from the end
      if (n < 0) n += this.length;
      // Out of bounds access is guaranteed to return undefined
      if (n < 0 || n >= this.length) return undefined;
      // Otherwise, this is just normal property access
      return this[n];
    }
    const TypedArray = Reflect.getPrototypeOf(Int8Array);
    for (const C of [Array, String, TypedArray]) {
      Object.defineProperty(C.prototype, "from_index", {
        value: from_index,
        writable: true,
        enumerable: false,
        configurable: true,
      });
    }
    // Check for already running tasks
    if (this.taskStarted != true) {
      this.checkExistingTasks();
    }
    // A global signal listener to perform the action
    if (this.submitOnEvent) {
      this.$root.$on(this.submitOnEvent, () => {
        if (this.isDisabled) return;
        // Bootstrap task if button is not disabled.
        this.bootstrapTask();
      });
    }
  },

  beforeDestroy() {
    if (this.submitOnEvent) {
      this.$root.$off(this.submitOnEvent);
    }
  },

  methods: {
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
      let response = await this.findOngoingAction(this.thing, this.action);
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
        false, // Don't handle errors,
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
      var result = response.data.status;
      this.taskStatus = result;
      if ((result == "running") | (result == "pending")) {
        // If the task is still running, we update progress/log,
        // and schedule another poll
        this.progress = response.data.progress;
        this.log = response.data.log;
      }
      // If task ends with an error
      else if (result == "error") {
        this.handleErrorResponse(response);
      }
    },

    handleErrorResponse(response) {
      // Pass the error string back with reject
      if (!this.progress) this.progress = 1;
      // Test whether the log is empty or the most recent message is not from an error
      // If so, return a default message
      if (
        (response.data.log.length == 0) |
        (response.data.log.from_index(-1).levelname != "ERROR")
      ) {
        var message = "Unexpected error, please check the logs";
      }
      // As LabThings Actions add the message from any raised exception to the log, the
      // last message in the log is the message from the Exception.
      // If the Exception was raised with no message, use a default.
      else {
        message =
          response.data.log.from_index(-1).message || "Unexpected error, please check the logs";
      }
      // Raise an Error with the chosen message
      throw new Error(message);
    },

    terminateTask: function () {
      if (this.taskUrl) {
        this.terminateAction(this.taskUrl);
      }
    },
  },
};
</script>

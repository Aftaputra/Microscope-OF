<template>
  <div class="log-container" ref="logContainer">
    <div v-if="log">
      <div v-for="(item, index) in log" :key="`log_entry_${index}`">
        {{ item.message }}
      </div>
    </div>
    <div v-if="taskStatus == 'error'" class="uk-alert uk-alert-danger">
      The task failed due to an error. There may be more information in the log.
    </div>
    <div v-if="taskStatus == 'cancelled'" class="uk-alert uk-alert-warning">
      The task was cancelled.
    </div>
    <div v-if="taskStatus == 'completed'" class="uk-alert uk-alert-success">
      The task completed successfully.
    </div>
  </div>
</template>

<script>
export default {
  name: "ActionLogDisplay",

  props: {
    taskStatus: {
      type: String,
      required: true
    },
    log: {
      type: Array,
      required: true
    }
  },

  watch: {
    log: function() {
      this.$nextTick(function() {
        let viewer = this.$refs.logContainer;
        viewer.scrollTop = viewer.scrollHeight;
      });
    }
  }
};
</script>

<style scoped>
.log-container {
  position: relative;
  overflow-y: scroll;
  overflow-x: auto;
}
</style>

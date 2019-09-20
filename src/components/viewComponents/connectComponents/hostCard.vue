<template>
	<div class="hostCard uk-card uk-card-default uk-card-hover uk-padding-remove uk-width-medium" v-bind:class="{ 'uk-card-secondary': $store.state.globalSettings.darkMode }">

    <div class="uk-card-media-top">
      <div class="snapshot-container uk-width-1-1 uk-height-auto">
        <img class="uk-width-1-1" v-bind:data-src="snapshotSrc" width="300" height="225" uk-img>
        <div v-if="!snapshotAvailable" class="uk-position-cover uk-flex uk-flex-center uk-flex-middle">Snapshot unavailable</div>
      </div>
    </div>

    <div class="uk-card-body uk-padding-small">
      <div class="uk-margin-small uk-margin-remove-left uk-margin-remove-right uk-flex uk-flex-middle">
        <div class="uk-width-expand host-description">
          <div class="host-description"><b>{{ name }}</b></div>
          <div class="host-description">{{ hostname }}:{{ port }}</div>
        </div>
        <a href="#" v-on:click="$emit('delete')" class="uk-icon uk-width-auto host-delete"><i class="material-icons">delete</i></a> 
      </div>
    </div>

    <div class="uk-card-footer uk-padding-small">
      <button 
        class="uk-button uk-button-default uk-form-small uk-float-right uk-margin uk-margin-remove-top uk-width-1-1"
        v-on:click="$emit('connect')"
        >Connect</button>
    </div>

	</div>
</template>

<script>
import UIkit from 'uikit';
import axios from 'axios'

// Export main app
export default {
  name: 'hostCard',

  props: {
    name: {
      type: String,
      required: true
    },
    hostname: {
      type: String,
      required: true
    },
    port: {
      type: Number,
      required: true
    }
  },

  data: function () {
    return {
      snapshotSrc: "",
      snapshotAvailable: false,
      polling: null
    }  
  },

  mounted() {
    // Try to load the microscope snapshot when mounted
    this.getSnapshotRequest()
  },

  beforeDestroy () {
    clearInterval(this.polling)
  },

  methods: {
    getSnapshotRequest: function() {
      // Send tag request
      axios.get(this.snapshotURL)
      .then(() => { 
        // Tell the view that a snapshot is available
        this.snapshotAvailable = true
        // Set the snapshot image src to the snapshot URL
        // Note, we add a timestamp argument to act as a cache-breaker
        this.snapshotSrc = `${this.snapshotURL}?${Date.now()}`
        // If not already polling, start polling
        if (this.polling === null) {
          this.updateSnapshotPoll()
        }
      })
      .catch(error => {
        // Tell the view that a snapshot is not available, and ignore
        this.snapshotAvailable = false
      })
    },

    updateSnapshotPoll: function() {
      this.polling = setInterval(() => {
        this.getSnapshotRequest()
      }, 15000)
    }
  },

  created: function () {
  },

  computed: {
    snapshotURL: function () {
      return `http://${this.hostname}:${this.port}/api/v1/snapshot`
    },
  }

}
</script>

<style>
.host-description {
  text-overflow: ellipsis;
  overflow: hidden;
}

.snapshot-container {
  position: relative;
}

img[data-src][src*='data:image'] { 
  background: rgba(127,127,127,0.1); 
}

</style>
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
    this.checkSnapshotAvailable()
  },

  beforeDestroy () {
    // Clear the polling timer
    if (this.polling !== null) {
      clearInterval(this.polling)
    }
  },

  methods: {
    checkSnapshotAvailable: function() {
      // Fetches the list of routes from the host, and starts
      // a snapshot timer if the snapshot route is available

      // Send tag request
      axios.get(this.routesURL)
      .then((response) => { 
        // If the host has a snapshot route available
        if ("/api/v1/snapshot" in response.data) {
          // Tell the view that a snapshot is available
          this.snapshotAvailable = true
          // Update the snapshot URL
          this.updateSnapshotURL()
          // If not already polling, start polling
          if (this.polling === null) {
            this.updateSnapshotPoll()
          }
        }

      })
      .catch(error => {
        // Tell the view that a snapshot is not available, and ignore
        this.snapshotAvailable = false
      })
    },

    updateSnapshotURL: function() {
      // Set the snapshot image src to the snapshot URL,
      // adding a timestamp argument to act as a cache-breaker
      this.snapshotSrc = `${this.snapshotURL}?${Date.now()}`
      console.log(`Updating snapshot URL to ${this.snapshotSrc}`)
    },

    updateSnapshotPoll: function() {
      // Start a timer to call updateSnapshotURL periodically
      this.polling = setInterval(() => {
        this.updateSnapshotURL()
      }, 15000)
    }
  },

  computed: {
    routesURL: function () {
      return `http://${this.hostname}:${this.port}/routes`
    },
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
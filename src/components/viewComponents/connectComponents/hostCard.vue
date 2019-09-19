<template>
	<div class="hostCard uk-card uk-card-default uk-card-hover uk-padding-remove uk-width-medium" v-bind:class="{ 'uk-card-secondary': $store.state.globalSettings.darkMode }">

    <div class="uk-card-body uk-padding-small uk-height-small">

      <div class="uk-margin-small uk-margin-remove-left uk-margin-remove-right uk-flex uk-flex-middle">
        <div class="uk-width-expand host-description"><b>{{ name }}</b> ({{ hostname }}:{{ port }})</div>
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
    }  
  },

  methods: {
  },

  created: function () {
  },

  computed: {
  }

}
</script>

<style>
.host-description {
  text-overflow: ellipsis;
  overflow: hidden;
}
</style>
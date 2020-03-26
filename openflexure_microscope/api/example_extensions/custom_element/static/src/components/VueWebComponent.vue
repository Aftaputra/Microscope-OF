<template>
  <div class="my-component-class">
    <h1>My Vue Web Component</h1>
    <div>Base URL: {{ componentBaseURL }}</div>
    <p>Host microscope name: {{ hostDeviceName }}</p>
    <p>{{ message }}</p>
    <br />
    <p>This cheeky little counter has all of its logic contained in a server-side component:</p>
    <button type="button" v-on:click="decrement()">-</button>
    <span>{{ value }}</span>
    <button type="button" v-on:click="increment()">+</button>
  </div>
</template>

<script>
import axios from 'axios';

export default {

  props: {
    'componentBaseURL': {
      required: false,
      default: null,
      type: String
    }
  },

  data: function() {
    return {
      value: 0,
      message: "",
      hostDeviceName: null
    };
  },

  mounted () {
    if (this.componentBaseURL){
      axios
      .get(`${this.componentBaseURL}`)
      .then(response => {
        console.log(response.data)
        this.hostDeviceName = response.data.title
      })
      .catch(function(error) {
        console.log("Error reading test json, probabl because of cors or something")
      })
    }
    else {
      this.message = "No componentBaseURL given"
    }

  },

  methods: {
    decrement: function() {
      this.value = this.value -1
    },

    increment: function() {
      this.value = this.value +1
    }
  }

}
</script>

<style scoped>
  .my-component-class {
    text-align: center;
  }
</style>
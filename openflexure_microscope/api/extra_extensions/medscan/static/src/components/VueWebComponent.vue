<template>
  <div class="medscan-component-class">
    <h1>Sample Scan Wizard</h1>
    <div>Base URL: {{ componentBaseURL }}</div>
    <p>Host microscope name: {{ hostDeviceName }}</p>
    <p>{{ message }}</p>
    <br />
    <p>This cheeky little counter has all of its logic contained in a server-side component:</p>
    <button type="button" v-on:click="decrement()">-</button>
    <span>{{ value }}</span>
    <button type="button" v-on:click="increment()">+</button>

    <hr />

    <form v-on:submit.prevent>
      <label for="username">Your name:</label>
      <input type="text" id="username" name="username" required />
      <br />
      <label for="patientID">Patient ID:</label>
      <input type="text" id="patientID" name="patientID" required />
      <br />
      <label for="currentTime">Current time (check this is correct):</label>
      <input type="datetime-local" id="currentTime" name="currentTime" v-model="currentTimeForm" />
    </form>
  </div>
</template>

<script>
import axios from "axios";

export default {
  props: {
    componentBaseURL: {
      required: false,
      default: "http://localhost:5000/api/v2",
      type: String
    }
  },

  data: function() {
    return {
      value: 0,
      message: "",
      hostDeviceName: null,
      currentTime: this.getLocalDatetimeString()
    };
  },

  mounted: function() {
    if (this.componentBaseURL) {
      axios
        .get(`${this.componentBaseURL}`)
        .then(response => {
          console.log(response.data);
          this.hostDeviceName = response.data.title;
        })
        .catch(function(error) {
          console.log(
            "Error reading test json, probabl because of cors or something"
          );
        });
    } else {
      this.message = "No componentBaseURL given";
    }
  },

  methods: {
    decrement: function() {
      this.value = this.value - 1;
    },

    increment: function() {
      this.value = this.value + 1;
    },

    getLocalDatetimeString: function() {
      var dt = new Date();
      var tzo = -dt.getTimezoneOffset(),
        dif = tzo >= 0 ? "+" : "-",
        pad = function(num) {
          var norm = Math.floor(Math.abs(num));
          return (norm < 10 ? "0" : "") + norm;
        };
      return (
        dt.getFullYear() +
        "-" +
        pad(dt.getMonth() + 1) +
        "-" +
        pad(dt.getDate()) +
        "T" +
        pad(dt.getHours()) +
        ":" +
        pad(dt.getMinutes()) +
        ":" +
        pad(dt.getSeconds()) +
        dif +
        pad(tzo / 60) +
        ":" +
        pad(tzo % 60)
      );
    }
  },

  computed: {
    currentTimeForm: {
      get() {
        // Chop the timezone information from the end
        return this.currentTime.substr(0, 19);
      },
      set(val) {
        console.log(val)
        // Get timezone
        var dt = new Date();
        var tzo = -dt.getTimezoneOffset(),
          dif = tzo >= 0 ? "+" : "-",
          pad = function(num) {
            var norm = Math.floor(Math.abs(num));
            return (norm < 10 ? "0" : "") + norm;
          };
        // Stick to the end of the new timestring from the form
        this.currentTime =
          val + dif + pad(tzo / 60) + ":" + pad(tzo % 60);
      }
    }
  }
};
</script>

<style scoped>
.medscan-component-class {
  text-align: left;
}
</style>
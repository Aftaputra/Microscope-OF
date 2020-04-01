<template>
  <div class="medscan-component-class">
    <h1>Sample Scan Wizard</h1>
    <div>Base URL: {{ componentBaseURL }}</div>
    <p>Host microscope name: {{ hostDeviceName }}</p>

    <hr />

    <form v-on:submit.prevent v-on:keyup.enter="increment()">
      <div id="step-user" v-show="stepValue==0">
        <h2>User information</h2>

        <label for="username">Your name:</label>
        <input type="text" id="username" name="username" v-model="username" required />
        <br />
        <label for="currentTime">Current time (check this is correct):</label>
        <input type="datetime-local" id="currentTime" name="currentTime" v-model="currentTimeForm" />
      </div>

      <div id="step-patient" v-show="stepValue==1">
        <h2>Patient information</h2>

        <label for="patientID">Patient ID:</label>
        <input type="text" id="patientID" name="patientID" v-model="patientID" required />
        <br />
      </div>

      <div id="step-sample" v-show="stepValue==2">
        <h2>Sample information</h2>

        <label>Sample type:</label>
        <br />
        <input type="radio" id="typeThin" value="thin" v-model="sampleType" />
        <label for="typeThin">Thin smear</label>
        <br />
        <input type="radio" id="typeThick" value="thick" v-model="sampleType" />
        <label for="typeThick">Thick smear</label>
        <br />
      </div>

      <div id="step-scan" v-show="stepValue==3">
        <h2>Start scan</h2>
(Confirm information)
        (Confirm scan parameters, just a radio box for selecting defaults)
        <p>{{this.payload}}</p>(Start button)
      </div>
    </form>

    <div id="form-stepper">
      <p>{{ message }}</p>
      <button v-show="stepValue == 3" type="button" v-on:click="restart()">Restart</button>
      <button v-show="stepValue > 0" type="button" v-on:click="decrement()">Previous</button>
      <button v-show="stepValue < 3" type="button" v-on:click="increment()">Next</button>
    </div>
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
      stepValue: 0,
      hostDeviceName: null,
      message: null,
      username: "",
      currentTime: this.getLocalDatetimeString(),
      patientID: "",
      sampleType: "thin"
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
      if (this.stepValue > 0) {
        this.stepValue = this.stepValue - 1;
      }
    },

    increment: function() {
      // Validate sections
      if (this.stepValue == 0) {
        if (!this.username) {
          this.message = "Please enter your name";
          return false;
        }
      }
      if (this.stepValue == 1) {
        if (!this.patientID) {
          this.message = "Please enter a patient ID";
          return false;
        }
      }
      // Upper bound on section number
      if (this.stepValue < 3) {
        this.stepValue = this.stepValue + 1;
        this.message = "";
        return true;
      }
    },

    restart: function() {
      this.stepValue = 0;
      this.patientID = "";
      this.currentTime = this.getLocalDatetimeString();
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
        console.log(val);
        // Get timezone
        var dt = new Date();
        var tzo = -dt.getTimezoneOffset(),
          dif = tzo >= 0 ? "+" : "-",
          pad = function(num) {
            var norm = Math.floor(Math.abs(num));
            return (norm < 10 ? "0" : "") + norm;
          };
        // Stick to the end of the new timestring from the form
        this.currentTime = val + dif + pad(tzo / 60) + ":" + pad(tzo % 60);
      }
    },

    payload: {
      get() {
        return {
          filename: `${this.patientID}_${this.sampleType}`,
          temporary: false,
          grid: [20, 20, 5],
          fast_autofocus: true,
          use_video_port: false,
          annotations: {
            patientID: this.patientID,
            username: this.username,
            clientDatetime: this.currentTime
          },
          tags: ["medscan"]
        };
      }
    }
  }
};
</script>

<style scoped>
.medscan-component-class {
  text-align: left;
}

input {
  display: block
}

button {
  margin: 0 10px 0 0;
  min-width: 100px;
}
</style>
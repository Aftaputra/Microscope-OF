<template>
  <div class="medscan">
    <div v-show="!scanUri">No scan extension found</div>
    <div v-show="scanUri">
      <h1>Sample Scan Wizard</h1>

      <form v-on:submit.prevent v-on:keyup.enter="increment()">
        <div id="step-user" v-show="stepValue==0">
          <h2>User information (1/4)</h2>

          <label for="username">Your name:</label>
          <input type="text" id="username" name="username" v-model="username" required />
          <br />
          <label for="currentTime">Current time (check this is correct):</label>
          <input
            type="datetime-local"
            id="currentTime"
            name="currentTime"
            v-model="currentTimeForm"
          />
        </div>

        <div id="step-patient" v-show="stepValue==1">
          <h2>Patient information (2/4)</h2>

          <label for="patientID">Patient ID:</label>
          <input type="text" id="patientID" name="patientID" v-model="patientID" required />
          <br />
        </div>

        <div id="step-sample" v-show="stepValue==2">
          <h2>Sample information (3/4)</h2>

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
          <h2>Start scan (4/4)</h2>

          <label>Check details:</label>
          <p>
            <b>Your name:</b>
            {{ username }}
          </p>
          <p>
            <b>Patient ID:</b>
            {{ patientID }}
          </p>
          <p>
            <b>Sample type:</b>
            {{ sampleType }}
          </p>
        </div>
      </form>

      <div id="form-stepper">
        <p class="warning">{{ message }}</p>
          <taskSubmitter
            v-if="scanUri"
            v-show="stepValue == 3"
            :base-url="baseURL"
            :submit-url="scanUri"
            :submit-data="payload"
            submit-label="Start scan"
            @submit="scanRunning=true"
            @response="scanRunning=false"
            @error="scanRunning=false"
          ></taskSubmitter>
        <br />

        <div class="grid-container">
          <button
            :disabled="stepValue <= 0 || scanRunning"
            type="button"
            v-on:click="decrement()"
          >Previous</button>
          <button
            :disabled="stepValue >= 3 || scanRunning"
            type="button"
            v-on:click="increment()"
          >Next</button>
        </div>
        <p>
          <button
            v-show="stepValue == 3"
            :disabled="scanRunning"
            type="button"
            v-on:click="restart()"
          >Restart</button>
        </p>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import taskSubmitter from "../genericComponents/taskSubmitter";

export default {
  components: {
    taskSubmitter
  },

  data: function() {
    return {
      scanUri: null,
      stepValue: 0,
      hostDeviceName: null,
      message: null,
      username: "",
      currentTime: this.getLocalDatetimeString(),
      patientID: "",
      sampleType: "thin",
      scanRunning: false,
      baseURL: `${window.location.origin}/api/v2`
    };
  },

  watch: {
    baseURL: function (val) {
      if (this.baseURL) {
        this.updateScanUri();
      } else {
        this.message = "No baseURL given";
      }
    },
  },

  mounted: function() {
    if (this.baseURL) {
      this.updateScanUri();
    } else {
      this.message = "No baseURL given";
    }
  },

  methods: {
    updateScanUri: function() {
      axios
        .get(this.pluginsUri) // Get a list of plugins
        .then(response => {
          console.log(response);
          var plugins = response.data;
          var foundExtension = plugins.find(
            e => e.title === "org.openflexure.scan"
          );
          // if ScanPlugin is enabled
          if (foundExtension) {
            // Get plugin action link
            this.scanUri = foundExtension.links.tile.href;
          }
        })
        .catch(error => {
          console.log(error); // Let mixin handle error
        });
    },

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
    pluginsUri: function() {
      return `${this.baseURL}/extensions`;
    },

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
          bayer: false,
          grid: [10, 10, 9],
          stride_size: [800, 600, 10],
          fast_autofocus: true,
          autofocus_dz: 2000,
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

<style>
.medscan {
  font-family: sans-serif;
  color: #444;
  text-align: left;
}

input[type="text"],
input[type="datetime-local"] {
  display: block;
  margin: 0 10px 0 0;
  width: 100%;
  height: 25px;
}

button {
  display: inline-block;
  box-sizing: border-box;
  margin: 0 10px 0 0;
  width: 100%;
  height: 25px;
  min-width: 100px;
}

.grid-container {
  display: grid;
  grid-template-columns: auto auto;
  grid-column-gap: 10px;
}

.warning {
  color: #c11;
  font-weight: bold;
  text-align: center;
}
</style>
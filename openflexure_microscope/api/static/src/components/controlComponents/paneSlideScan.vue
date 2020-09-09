<template>
  <div class="medscan">
    <div v-show="!scanUri">No scan extension found</div>
    <div v-show="scanUri">
      <h1>Sample Scan Wizard</h1>

      <form @submit.prevent @keyup.enter="increment()">
        <div v-show="stepValue == 0" id="step-user">
          <h2>User information (1/4)</h2>

          <label for="username">Your name:</label>
          <input
            id="username"
            v-model="username"
            type="text"
            name="username"
            required
          />
          <br />
          <label for="currentTime">Current time (check this is correct):</label>
          <input
            id="currentTime"
            v-model="currentTimeForm"
            type="datetime-local"
            name="currentTime"
          />
        </div>

        <div v-show="stepValue == 1" id="step-patient">
          <h2>Patient information (2/4)</h2>

          <label for="patientID">Patient ID:</label>
          <input
            id="patientID"
            v-model="patientID"
            type="text"
            name="patientID"
            required
          />
          <br />
        </div>

        <div v-show="stepValue == 2" id="step-sample">
          <h2>Sample information (3/4)</h2>

          <label>Sample type:</label>
          <br />
          <input id="typeThin" v-model="sampleType" type="radio" value="thin" />
          <label for="typeThin">Thin smear</label>
          <br />
          <input
            id="typeThick"
            v-model="sampleType"
            type="radio"
            value="thick"
          />
          <label for="typeThick">Thick smear</label>
          <br />
        </div>

        <div v-show="stepValue == 3" id="step-scan">
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
          @submit="scanRunning = true"
          @response="scanRunning = false"
          @error="scanRunning = false"
        ></taskSubmitter>
        <br />

        <div class="grid-container">
          <button
            :disabled="stepValue <= 0 || scanRunning"
            type="button"
            @click="decrement()"
          >
            Previous
          </button>
          <button
            :disabled="stepValue >= 3 || scanRunning"
            type="button"
            @click="increment()"
          >
            Next
          </button>
        </div>
        <p>
          <button
            v-show="stepValue == 3"
            :disabled="scanRunning"
            type="button"
            @click="restart()"
          >
            Restart
          </button>
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

  computed: {
    pluginsUri: function() {
      return `${this.$store.getters.baseUri}/api/v2/extensions`;
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
  },

  watch: {
    baseURL: function(val) {
      if (this.baseURL) {
        this.updateScanUri();
      } else {
        this.message = "No baseURL given";
      }
    }
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
          this.modalError(error); // Let mixin handle error
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
  }
};
</script>

<style>
.medscan {
  font-family: sans-serif;
  color: #444;
  text-align: left;
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

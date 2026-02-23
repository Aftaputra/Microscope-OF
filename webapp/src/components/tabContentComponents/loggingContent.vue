<template>
  <div ref="loggingDisplay" class="uk-padding uk-padding-remove-top">
    <!-- Logging nav bar -->
    <nav class="logging-navbar uk-navbar-container uk-navbar-transparent" uk-navbar="mode: click">
      <!-- Left side controls -->
      <div class="uk-navbar-left uk-padding-remove-top uk-padding-remove-bottom">
        <select v-model="filterLevel" class="uk-select">
          <option v-for="level in allLevels" :key="level">{{ level }}</option>
        </select>
      </div>

      <!-- Right side buttons -->
      <div class="uk-navbar-right">
        <div class="uk-grid">
          <div>
            <button
              class="uk-button uk-button-default uk-width-1-1"
              type="button"
              @click="updateLogs()"
            >
              Refresh Logs
            </button>
          </div>
          <div>
            <EndpointButton
              class="uk-button uk-width-1-1"
              :url="logFileURI"
              button-label="Download Log File"
              :button-primary="false"
            />
          </div>
        </div>
      </div>
    </nav>

    <!-- Logging items -->
    <div class="uk-width-xlarge uk-align-center">
      <div
        v-for="item in pagedItems"
        :key="item.sequence"
        uk-alert
        class="logging-entry"
        :class="{
          'uk-alert-warning uk-alert': item.level == 'WARNING',
          'uk-alert-danger uk-alert': item.level == 'ERROR',
        }"
      >
        <div class="logging-header">
          <span class="log-date">
            {{ formatDateTime(item.timestamp) }}
          </span>
          <span class="log-level">
            {{ item.level }}
          </span>
        </div>
        <div class="logging-entry-body">
          <div class="logging-summary">
            {{ item.summary }}
          </div>
          <div class="more-info-container">
            <a
              v-if="(item.summary != item.message) & !item.expanded"
              class="more-info"
              @click="item.expanded = true"
            >
              More info...
            </a>
            <a
              v-if="(item.summary != item.message) & item.expanded"
              class="more-info"
              @click="item.expanded = false"
            >
              Hide info...
            </a>
          </div>
        </div>
        <!-- eslint-disable vue/no-v-html -->
        <div v-if="item.expanded" class="logging-message" v-html="item.message"></div>
        <!-- eslint-enable -->
      </div>
      <PaginateLinks
        :total-pages="totalPages"
        :current-page="currentPage"
        @change-page="changePage"
      />
    </div>
  </div>
</template>

<script>
import axios from "axios";
import PaginateLinks from "@/components/genericComponents/paginateLinks.vue";
import EndpointButton from "../labThingsComponents/endpointButton.vue";
import { useIntersectionObserver } from "@vueuse/core";

export default {
  name: "LoggingContent",

  components: {
    PaginateLinks,
    EndpointButton,
  },

  emits: ["scrollTop"],

  data: function () {
    return {
      maxitems: 20,
      currentPage: 1,
      logs: [],
      allLevels: ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
      filterLevel: "WARNING",
    };
  },

  computed: {
    filteredLevels: function () {
      let cutoffIndex = this.allLevels.indexOf(this.filterLevel);
      return this.allLevels.slice(cutoffIndex, -1);
    },
    filteredItems: function () {
      var items = [];
      for (var item of this.logs) {
        // Add to capture list if matched
        if (this.filteredLevels.includes(item.level)) {
          items.push(item);
        }
      }

      return items;
    },
    logURI: function () {
      return `${this.$store.getters.baseUri}/log/`;
    },
    logFileURI: function () {
      return `${this.$store.getters.baseUri}/logfile/`;
    },
    pagedItems: function () {
      let startIndex = (this.currentPage - 1) * this.maxitems;
      return this.filteredItems.slice(startIndex, startIndex + this.maxitems);
    },
    totalPages: function () {
      return Math.floor(this.filteredItems.length / this.maxitems);
    },
  },

  mounted() {
    useIntersectionObserver(
      this.$refs.loggingDisplay,
      ([{ isIntersecting }]) => {
        this.visibilityChanged(isIntersecting);
      },
      {
        threshold: 0.0,
      },
    );
  },

  methods: {
    changePage(page) {
      if (page >= 1 && page <= this.totalPages && this.currentPage != page) {
        this.$emit("scrollTop");
        this.currentPage = page;
      }
    },
    visibilityChanged(isVisible) {
      if (isVisible) {
        this.updateLogs();
      }
    },
    async updateLogs() {
      let response = await axios.get(this.logURI);
      let lines = response.data.split("\n");
      let logs = [];
      let regexp = /^\[(.+?)\] \[(DEBUG|INFO|WARNING|ERROR|CRITICAL)\] (.*)$/;
      for (let line of lines) {
        if (line.length > 0) {
          let m = line.match(regexp);
          if (m) {
            logs.push({
              timestamp: m[1],
              level: m[2],
              summary: m[3],
              message: this.escapeText(m[3]),
              sequence: logs.length,
              expanded: false,
            });
          } else if (logs) {
            // If a line does not look like a log entry, append it to the last
            // log entry (i.e. allow multi-line messages)
            let entry = logs[logs.length - 1];
            m = line.match(/^( *)(\^+)/); // detect python stack trace "underlines"
            if (m) {
              let linestart = entry.message.lastIndexOf("\n") + 1;
              let ustart = linestart + m[1].length;
              let uend = ustart + m[2].length;
              entry.message =
                entry.message.substring(0, ustart) +
                "<u>" +
                entry.message.substring(ustart, uend) +
                "</u>" +
                entry.message.substring(uend);
            } else {
              entry.message += "\n" + this.escapeText(line);
              if (entry.message.startsWith("Traceback")) {
                entry.summary = line; // For tracebacks, the last line is the best summary
              }
            }
          } else {
            // if there's no existing log message to append to, discard lines
            // until we find one.
            continue;
          }
        }
      }
      this.logs = logs.reverse(); // Display in reverse chronological order
    },
    formatDateTime: function (isoDateTimeString) {
      isoDateTimeString = isoDateTimeString.replace(",", ".");
      let date = new Date(isoDateTimeString);
      return date.toLocaleDateString() + " " + date.toLocaleTimeString();
    },
    escapeText: function (unsafeText) {
      let div = document.createElement("div");
      div.innerText = unsafeText;
      return div.innerHTML;
    },
  },
};
</script>

<style lang="less" scoped>
// Pinched from ui-kit
@info-bg-color: #d5d5d5;
@warning-color: #faa05a;
@warning-bg-color: #fff6ee;
@error-color: #f0506e;
@error-bg-color: #fef4f6;

.logging-navbar {
  border-width: 0 0 1px 0;
  border-style: solid;
  border-color: rgba(180, 180, 180, 0.25);
  margin-bottom: 30px;
  height: 80px;
}
.logging-entry {
  white-space: break-spaces;
  padding: 0;
  overflow: hidden;
}

.logging-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  padding: 6px 12px;
  background: darken(@info-bg-color, 15%);
}

.uk-light .logging-header {
  background: darken(@info-bg-color, 35%);
  color: lighten(@info-bg-color, 35%);
}

.uk-alert-warning .logging-header {
  background: darken(@warning-bg-color, 15%);
  color: darken(@warning-color, 15%);
}

.uk-light .uk-alert-warning .logging-header {
  background: desaturate(darken(@warning-color, 15%), 10%);
  color: darken(@warning-bg-color, 5%);
}

.uk-alert-danger .logging-header {
  background: darken(@error-bg-color, 15%);
  color: darken(@error-color, 15%);
}

.uk-light .uk-alert-danger .logging-header {
  background: desaturate(darken(@error-color, 10%), 10%);
  color: darken(@error-bg-color, 5%);
}

.logging-entry-body {
  padding: 15px 29px 15px 15px;
}

.logging-summary {
  font-weight: 500;
}

.logging-message {
  font-family: monospace;
  overflow-x: auto;
  text-wrap: nowrap;
  margin-left: 15px;
  max-height: 60vh;
  scrollbar-width: thin;
  scrollbar-color: #888 transparent;
}

.logging-message::-webkit-scrollbar {
  width: 8px;
}

.logging-message::-webkit-scrollbar-thumb {
  background: #888;
  border-radius: 6px;
}
.more-info-container {
  display: flex;
}
.more-info {
  color: inherit;
  text-decoration: underline;
  margin-left: auto;
}
</style>

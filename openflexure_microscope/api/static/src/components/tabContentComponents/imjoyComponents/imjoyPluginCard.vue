<template>
  <div
    class="uk-card uk-card-hover uk-card-default uk-width-medium"
    :class="{ 'uk-card-secondary': $store.state.darkMode }"
  >
    <a href="#" class="uk-link-text" @click="$emit('click')">
      <h3 class="uk-card-header">{{ name }}</h3>
      <div class="uk-card-body">
        <div class="uk-align-center">
          <img
            v-if="iconURL"
            class="uk-width-1-1"
            :data-src="iconURL"
            :alt="name + ' icon'"
            uk-img
          />
          <i v-if="!iconURL" class="material-icons" style="font-size:96px">
            {{ iconName }}
          </i>
        </div>
        <slot></slot>
      </div>
    </a>
  </div>
</template>

<script>
export default {
  name: "ImjoyPluginCard",

  props: {
    name: {
      type: String,
      required: true
    },
    iconURL: {
      type: String,
      required: false,
      default: () => ""
    },
    iconName: {
      type: String,
      required: false,
      default: () => "extension"
    }
  }
};
</script>

<template>
  <div>
    <label class="uk-form-label">{{ label }}</label>

    <input
      class="uk-input uk-form-small"
      type="text"
      :name="name"
      :value="value"
      :placeholder="placeholder"
      @input="$emit('input', $event.target.value)"
    />
  </div>
</template>

<script>
export default {
  name: "TextInput",

  props: {
    placeholder: {
      type: String,
      required: true
    },
    label: {
      type: String,
      required: true
    },
    name: {
      type: String,
      required: true
    },
    value: {
      type: String,
      required: true
    }
  }
};
</script>

<style scoped></style>

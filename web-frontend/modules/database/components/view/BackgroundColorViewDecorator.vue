<template>
  <div
    class="background-color-decorator"
    :style="value ? { 'background-color': value } : {}"
  >
    <slot />
  </div>
</template>

<script>
export default {
  name: 'BackgroundColorViewDecorator',
  props: {
    value: {
      type: String,
      required: false,
      default: null,
    },
  },
}
</script>

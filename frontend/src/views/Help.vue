<template>
  <el-card>
    <div v-if="markdown">
      <!-- <div v-html="rendered"></div> -->
      <MdPreview v-model="rendered" />
    </div>
    <div v-else>
      <h2>{{ $t('help.title') }}</h2>
      <p>{{ $t('help.hint') }}</p>
    </div>
  </el-card>
</template>
<script setup>
import { computed } from 'vue';
// import MarkdownIt from 'markdown-it';
import { MdPreview } from 'md-editor-v3';
import 'md-editor-v3/lib/style.css';

const props = defineProps({ markdown: { type: String, default: '' } });
// const md = new MarkdownIt({ html: true, linkify: true, typographer: true });
// const rendered = computed(() => props.markdown ? md.render(props.markdown) : '');

const rendered = computed(() => props.markdown || '');
</script> 
<script>
import { ref, toRef } from 'vue'

import { getKKSByTextMasksFromSearch } from '../../stores'

export default {
  name: 'UTemplate',
  props: {
    position: Number,
    disabledFlag: Boolean,
    template: String,
    countOfTemplates: Number,
    types: Array()
  },
  emits: ['addUTemplate', 'removeUTemplate', 'changeTemplate', 'searchPressed'],
  setup(props, context) {
    const currentPosition = toRef(props, 'position')
    // const currentPosition = ref(props.position)

    // const templateText = toRef(props, 'template')
    const currentFlag = toRef(props, 'disabledFlag')
    const templateText = ref(props.template)
    // const currentFlag = ref(props.disabledFlag)

    const countOfTemplatesLength = toRef(props, 'countOfTemplates')
    // const countOfTemplatesLength = ref(props.countOfTemplates)

    const chosenTypes = toRef(props, 'types')
    // const chosenTypes = ref(props.types)

    const changeTemplateText = () => {
      context.emit('changeTemplate', currentPosition.value, templateText.value)
    }

    const onAddButtonClick = () => {
      context.emit('addUTemplate', currentPosition.value)
    }

    const onRemoveButtonClick = () => {
      context.emit('removeUTemplate', currentPosition.value)
    }

    const dialogSearchActive = ref(false)
    const dialogSearchedTagsTextArea = ref('')
    const countOfTags = ref(0)

    const onButtonDialogSearchActive = async () => {
      context.emit('searchPressed')
      localComponentTagsLoadingFlag.value = true
      await getKKSByTextMasksFromSearch(
        templateText,
        chosenTypes.value,
        dialogSearchedTagsTextArea,
        countOfTags
      )
      localComponentTagsLoadingFlag.value = false
      dialogSearchActive.value = true
      context.emit('searchPressed')
    }

    const localComponentTagsLoadingFlag = ref(false)

    const onSearchButtonClick = async () => {
      localComponentTagsLoadingFlag.value = true
      await getKKSByTextMasksFromSearch(
        templateText,
        chosenTypes.value,
        dialogSearchedTagsTextArea,
        countOfTags
      )
      localComponentTagsLoadingFlag.value = false
      dialogSearchActive.value = true
    }

    // onMounted(async () => {
    //   localComponentTagsLoadingFlag.value = true
    //   await getKKSByTextMasksFromSearch(templateText, chosenTypes.value, dialogSearchedTagsTextArea, countOfTags)
    //   localComponentTagsLoadingFlag.value = false
    // })

    return {
      currentPosition,
      templateText,
      changeTemplateText,
      currentFlag,
      countOfTemplatesLength,
      onAddButtonClick,
      onRemoveButtonClick,
      dialogSearchActive,
      dialogSearchedTagsTextArea,
      countOfTags,
      onButtonDialogSearchActive,
      localComponentTagsLoadingFlag,
      onSearchButtonClick
    }
  }
}
</script>

<template>
  <div class="components-between-hr-margin-bottom"></div>
  <div class="col-1">
    {{ currentPosition }}
  </div>
  <div class="col-7">
    <FloatLabel>
      <InputText
        v-model="templateText"
        type="text"
        :id="'template-text-' + currentPosition"
        :disabled="currentFlag || localComponentTagsLoadingFlag"
        @change="changeTemplateText"
        style="width: 100%"
      >
      </InputText>
      <label :for="'template-text-' + currentPosition">Введите шаблон или теги сигналов</label>
    </FloatLabel>
  </div>
  <div class="col-2">
    <Button
      @click="onButtonDialogSearchActive"
      label="Поиск тегов"
      icon="pi pi-search"
      iconPos="right"
      :disabled="currentFlag || localComponentTagsLoadingFlag"
      style="width: 90%"
    />
    <Dialog
      v-model:visible="dialogSearchActive"
      :visible="dialogSearchActive"
      :closable="true"
      header="Поиск тегов"
      position="center"
      :modal="true"
      :draggable="true"
      :style="{ width: '50rem' }"
    >
      <div class="container">
        <div class="row">
          <div class="col">
            <label :for="'template-search-text-' + currentPosition"
              >Введите шаблон или теги сигналов</label
            >
          </div>
        </div>
        <div class="row">
          <div class="col-11">
            <InputText
              v-model="templateText"
              type="text"
              :id="'template-search-text-' + currentPosition"
              :disabled="currentFlag || localComponentTagsLoadingFlag"
              @change="changeTemplateText"
              style="width: 100%"
            >
            </InputText>
          </div>
          <div class="col-1">
            <Button
              @click="onSearchButtonClick"
              icon="pi pi-search"
              :disabled="currentFlag || localComponentTagsLoadingFlag"
            />
          </div>
        </div>
        <div class="row">
          <div class="col">
            Количество запрошенных тегов: <b>{{ countOfTags }}</b>
          </div>
        </div>
        <div class="row">
          <div class="col">
            <label :for="'template-search-text-area' + currentPosition"
              >Найденные по шаблону теги</label
            >
            <TextArea
              :id="'template-search-text-area' + currentPosition"
              v-model="dialogSearchedTagsTextArea"
              rows="10"
              cols="80"
              readonly
              :disabled="currentFlag || localComponentTagsLoadingFlag"
              :style="{ resize: 'none', 'overflow-y': scroll, width: '100%' }"
              >{{ dialogSearchedTagsTextArea }}</TextArea
            >
          </div>
        </div>
      </div>
    </Dialog>
  </div>
  <div class="col-1" v-if="countOfTemplatesLength === 1"></div>
  <div class="col-1 text-end" v-else>
    <Button
      @click="onRemoveButtonClick"
      icon="pi pi-minus"
      :disabled="currentFlag || localComponentTagsLoadingFlag"
    />
  </div>
  <div class="col-1 text-end">
    <Button
      @click="onAddButtonClick"
      icon="pi pi-plus"
      :disabled="currentFlag || localComponentTagsLoadingFlag"
    />
  </div>
</template>

<style>
.components-between-hr-margin-bottom {
  margin-bottom: 15px;
}
</style>

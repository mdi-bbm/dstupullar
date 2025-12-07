<template>
  <div class="annotation-tools">
    <div class="tools-header">
      <h3 class="text-h6">{{ $t('annotationtools.title') }}</h3>
      <v-btn icon size="small" @click="$emit('close')">
        <v-icon>mdi-close</v-icon>
      </v-btn>
    </div>

    <v-divider></v-divider>

    <div class="tools-content">
    <v-divider v-if="annotationMode === 'segmentation'"></v-divider>

      <div class="tool-section">
        <h4 class="text-subtitle-2 mb-2">{{ $t('annotationtools.modeofjob') }}</h4>
        
        <div class="tool-buttons">
      
          <v-btn 
            v-if ="annotationMode === 'detection'"
            variant="outlined" 
            size="small" 
            class="tool-btn"
            :color="activeTool === 'rectangle' ? 'primary' : undefined"
            @click="setActiveTool('rectangle')"
          >
            <v-icon>mdi-select-drag</v-icon>
            {{ $t('annotationtools.rectangle') }}
          </v-btn>

          <v-btn 
            v-if ="annotationMode === 'segmentation'"
            variant="outlined" 
            size="small" 
            class="tool-btn"
            :color="activeTool === 'brush' ? 'primary' : undefined"
            @click="setActiveTool('brush')"
          >
            <v-icon>mdi-brush</v-icon>
            {{ $t('annotationtools.brush') }}
          </v-btn>

          <v-btn 
            variant="outlined" 
            size="small" 
            class="tool-btn"
            :color="activeTool === 'zoom' ? 'primary' : undefined"
            @click="setActiveTool('zoom')"
          >
            <v-icon>mdi-magnify</v-icon>
            {{ $t('annotationtools.zoom') }}
          </v-btn>
          <v-btn 
            variant="outlined" 
            size="small" 
            class="tool-btn"
            :color="activeTool === 'ruler' ? 'primary' : undefined"
            @click="setActiveTool('ruler')"
          >
            <v-icon>mdi-ruler</v-icon>
            {{ $t('annotationtools.ruler') }}
          </v-btn>
          <div class="tool-section">
            <div class="d-flex align-center justify-space-between mb-2">
              <h4 class="text-subtitle-2 mb-0">{{ $t('annotationtools.settingsruler') }}</h4>
              <v-btn
                :disabled="!props.is_admin && !props.is_editor"
                icon="mdi-cog"
                variant="text"
                size="small"
                @click="showRulerDialog = true"
                :title="$t('annotationtools.rulerconfiguration')"
              >
                <v-icon>mdi-cog</v-icon>
              </v-btn>
            </div>

            <v-select
              v-model="selectedScale"
              :items="rulerScales"
              item-title="label"
              return-object
              density="compact"
              variant="outlined"
              :placeholder="rulerScales.length ? $t('annotationtools.selectscale') : $t('annotationtools.noscales')"
              :disabled="!rulerScales.length"
            >
              <template v-slot:item="{ props, item }">
                <v-list-item v-bind="props">
                  <template v-slot:prepend>
                    <v-icon>mdi-ruler</v-icon>
                  </template>
                </v-list-item>
              </template>
              
              <template v-slot:selection="{ item }">
                <div v-if="item.raw">
                  <strong>{{ item.raw.barcode }}</strong> - {{ item.raw.value_per_pixel }} {{ item.raw.unit }}
                </div>
                <span v-else>{{ item.title }}</span>
              </template>
            </v-select>


            <div v-if="selectedScale" class="scale-info mt-2">
              <v-chip size="small" color="primary">
                {{ selectedScale.value_per_pixel }} {{ selectedScale.unit }} {{ $t('annotationtools.perpixel') }}
              </v-chip>
              <div class="text-caption text-grey mt-1">
                {{ $t('annotationtools.barcode') }} {{ selectedScale.barcode }}
              </div>
            </div>

            <div v-else-if="!rulerScales.length" class="text-center py-4">
              <v-icon size="48" color="grey-lighten-1">mdi-ruler-square</v-icon>
              <div class="text-caption text-grey mt-2">{{ $t('annotationtools.noscales') }}</div>
              <v-btn 
                size="small" 
                variant="text" 
                @click="showRulerDialog = true"
                class="mt-2"
              >
                {{ $t('annotationtools.addscale') }}
              </v-btn>
            </div>
            
          </div>

          
          <v-dialog v-model="showRulerDialog" max-width="600">
            <v-card>
              <v-card-title>{{ $t('annotationtools.rulerconfiguration') }}</v-card-title>
              
              <v-card-text>
               
                <div v-if="rulerScales.length" class="mb-4">
                  <h5 class="text-h6 mb-3">{{ $t('annotationtools.existingruler') }}</h5>
                  <v-list lines="two">
                    <v-list-item
                      v-for="(scale, index) in rulerScales"
                      :key="index"
                      class="mb-2"
                    >
                      <template v-slot:prepend>
                        <v-icon>mdi-ruler</v-icon>
                      </template>

                      <v-list-item-title>
                        {{ scale.barcode }} - {{ scale.value_per_pixel }} {{ scale.unit }}
                      </v-list-item-title>
                      
                      <template v-slot:append>
                        <div class="d-flex gap-1">
                          <v-btn
                            icon
                            size="small"
                            variant="text"
                            @click="editScale(scale, index)"
                            :title="$t('annotationtools.edit')"
                          >
                            <v-icon>mdi-pencil</v-icon>
                          </v-btn>
                          <v-btn
                            icon
                            size="small"
                            variant="text"
                            color="error"
                            @click="deleteScale(index)"
                            :title="$t('annotationtools.delete')"
                          >
                            <v-icon>mdi-delete</v-icon>
                          </v-btn>
                        </div>
                      </template>
                    </v-list-item>
                  </v-list>
                </div>

                
                <h5 class="text-h6 mb-3">{{ editingScale ? $t('annotationtools.edit') : $t('annotationtools.add') }}</h5>
                <div class="d-flex gap-2">
                  <v-text-field
                    v-model="newScale.barcode"
                    :label="$t('annotationtools.barcode')"
                    density="compact"
                    variant="outlined"
                  />
                  <v-text-field
                    v-model="newScale.value_per_pixel"
                    :label="$t('annotationtools.valueperpixel')"
                    density="compact"
                    variant="outlined"
                    type="number"
                  />
                  <v-select
                    v-model="newScale.unit"
                    :items="['nm', 'µm', 'mm', 'cm']"
                    :label="$t('annotationtools.unit')"
                    density="compact"
                    variant="outlined"
                  />
                  <v-btn 
                    
                    color="primary" 
                    @click="saveScale"
                    :disabled="!newScale.barcode || !newScale.value_per_pixel "
                  >
                    {{ editingScale ? $t('annotationtools.save') : $t('annotationtools.add') }}
                  </v-btn>
                  <v-btn 
                    v-if="editingScale"
                    @click="cancelEdit"
                  >
                    {{ $t('annotationtools.cancel') }}
                  </v-btn>
                </div>
              </v-card-text>

              <v-card-actions>
                <v-spacer></v-spacer>
                <v-btn color="primary" @click="showRulerDialog = false">{{ $t('annotationtools.close') }}</v-btn>
              </v-card-actions>
            </v-card>
          </v-dialog>
        </div>
      </div>

      <v-divider></v-divider>

      <div class="tool-section">
        <div class="d-flex align-center justify-space-between mb-2">
          <h4 class="text-subtitle-2 mb-0">{{ $t('annotationtools.activeclass') }}</h4>
          <v-btn
            :disabled="!props.is_admin && !props.is_editor"
            icon="mdi-cog"
            variant="text"
            size="small"
            @click="showClassDialog = true"
            :title="$t('annotationtools.classsettings')"
          >
            <v-icon>mdi-cog</v-icon>
          </v-btn>
        </div>

        <v-select
          v-model="activeClass"
          :items="sortedAnnotationClasses"
          item-title="name"
          item-value="id"
          density="compact"
          variant="outlined"
          return-object
        >
          <template v-slot:item="{ props, item }">
            <v-list-item v-bind="props">
              <template v-slot:prepend>
                <div class="d-flex align-center">
                  
                  <v-btn
                    icon
                    variant="text"
                    size="x-small"
                    @click.stop="toggleFavoriteClass(item.raw)"
                    :color="item.raw.favorite ? 'amber' : 'grey'"
                  >
                    <v-icon>
                      {{ item.raw.favorite ? 'mdi-star' : 'mdi-star-outline' }}
                    </v-icon>
                  </v-btn>
                 
                  <v-icon :color="item.raw.color" class="ml-1">mdi-circle</v-icon>
                </div>
              </template>
            </v-list-item>
          </template>
          <template v-slot:selection="{ item }">
            <div class="d-flex align-center">
              
              <v-btn
                v-if="item.raw.favorite"
                icon
                variant="text"
                size="x-small"
                color="amber"
              >
                <v-icon small>mdi-star</v-icon>
              </v-btn>
              <v-icon :color="item.raw.color" class="mr-2">mdi-circle</v-icon>
              <span>{{ item.title }}</span>
            </div>
          </template>
        </v-select>
      </div>
 
      <v-dialog v-model="showClassDialog" max-width="400">
        <v-card>
          <v-card-title>{{ $t('annotationtools.classsettings') }}</v-card-title>
          
          <v-card-text>
            <!-- Выбор или создание класса -->
            <v-combobox
              v-model="selectedClass"
              :items="annotationClasses"
              item-title="name"
              item-value="id"
              :label="$t('annotationtools.class')"
              variant="outlined"
              return-object
            >
              <template v-slot:item="{ props, item }">
                <v-list-item v-bind="props">
                  <template v-slot:prepend>
                    <v-icon :color="item.raw.color">mdi-circle</v-icon>
                  </template>
                </v-list-item>
              </template>
              <template v-slot:selection="{ item }">
                <v-icon :color="item.raw.color" class="mr-2">mdi-circle</v-icon>
                <span>{{ item.title }}</span>
              </template>
            </v-combobox>

            <div class="mt-4">
              <div class="text-caption mb-2">{{ $t('annotationtools.classcolor') }}</div>
              <v-color-picker
                v-model="classColor"
                mode="hex"
                hide-inputs
                swatches-max-height="120"
              ></v-color-picker>
              
          
              <div class="text-center mt-3">
                <v-icon :color="classColor" size="48">mdi-circle</v-icon>
                <div class="text-caption">{{ selectedClass?.name }}</div>
              </div>
            </div>
          </v-card-text>

          <v-card-actions>
       
            <v-btn 
              v-if="selectedClass && selectedClass.id" 
              color="error" 
              variant="text"
              @click="deleteClass"
              
            >
              <v-icon>mdi-delete</v-icon>
              {{ $t('annotationtools.delete') }}
            </v-btn>
            
            <v-spacer></v-spacer>
            <v-btn @click="showClassDialog = false">{{ $t('annotationtools.cancel') }}</v-btn>
            <v-btn color="primary" @click="saveClass">{{ $t('annotationtools.save') }}</v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
      <v-divider></v-divider>

     

      <v-divider></v-divider>

      <div class="tool-section">
        <h4 class="text-subtitle-2 mb-2">{{ $t('annotationtools.actions') }}</h4>
        <div class="action-buttons">
          <v-btn 
           :disabled="!props.is_admin && !props.is_editor"
            variant="outlined" 
            color="error" 
            size="small"
            @click="$emit('clear-annotations')"
            
          >
            <v-icon>mdi-delete</v-icon>
            {{ $t('annotationtools.clear') }}
          </v-btn>
          <v-btn 
            :disabled="!props.is_admin && !props.is_editor"
            variant="outlined" 
            color="primary" 
            size="small"
            @click="$emit('save-annotations')"
            
          >
            <v-icon>mdi-content-save</v-icon>
            {{ $t('annotationtools.save') }}
          </v-btn>
        </div>
      </div>
       <div class="tool-section">
      <h4 class="text-subtitle-2 mb-2">{{ $t('annotationtools.image') }}</h4>
      
      <div class="slider-control">
        <div class="slider-label">
          <v-icon small>mdi-opacity</v-icon>
          <span>{{ $t('annotationtools.noopacity') }} {{ annotationOpacity }}%</span>
        </div>
        <v-slider
          v-model="annotationOpacity"
          min="0"
          max="100"
          step="5"
          :thumb-label="false"
          density="compact"
        ></v-slider>
      </div>

  
      <div class="slider-control">
        <div class="slider-label">
          <v-icon small>mdi-brightness-6</v-icon>
          <span>{{ $t('annotationtools.brightness') }} {{ imageBrightness }}%</span>
        </div>
        <v-slider
          v-model="imageBrightness"
          min="0"
          max="200"
          step="10"
          :thumb-label="false"
          density="compact"
        ></v-slider>
      </div>


      <div class="slider-control">
        <div class="slider-label">
          <v-icon small>mdi-contrast-circle</v-icon>
          <span>{{ $t('annotationtools.contrast') }} {{ imageContrast }}%</span>
        </div>
        <v-slider
          v-model="imageContrast"
          min="0"
          max="200"
          step="10"
          :thumb-label="false"
          density="compact"
        ></v-slider>
      </div>
    </div>

    <v-divider></v-divider>

   
    <div class="tool-section" v-if="annotationMode === 'segmentation'">
      <h4 class="text-subtitle-2 mb-2">{{ $t('annotationtools.brushSettings') }}</h4>
      

      <div class="slider-control">
        <div class="slider-label">
          <v-icon small>mdi-border-style</v-icon>
          <span>{{ $t('annotationtools.brushSize') }} {{ brushSize }}</span>
        </div>
        <v-slider
          v-model="brushSize"
          min="1"
          max="50"
          step="1"
          :thumb-label="false"
          density="compact"
        ></v-slider>
      </div>
    </div>
    </div>
  </div>
</template>

<script setup>
import { on } from 'events'
import { ref, computed, watch } from 'vue'
const { t } = useI18n()
const props = defineProps({
  annotationMode: String,
  datasetId: String,
  lableProperties: Object, 
  favoriteClasses: Array, 
  is_admin: Boolean, 
  is_editor: Boolean
})
const { authGet, authPost, authUpload } = useAuthFetch()
const emit = defineEmits(['close', 'clear-annotations', 'save-annotations'])
const activeTool = ref(null)

const brushSize = ref(20) 
const annotationOpacity = ref(100) 
const imageBrightness = ref(100)  
const imageContrast = ref(100)    
const rulerscale = ref([])
const selectedScale = ref(null)
const showRulerDialog = ref(false)
const editingScale = ref(null)

const newScale = ref({
  barcode: '',
  value_per_pixel: '',
  unit: 'µm'
})

const rulerScales = computed(() => {
  return rulerscale.value.map((scale, index) => ({
    ...scale,
    id: index,
    label: `${scale.barcode} - ${scale.value_per_pixel} ${scale.unit}`
  }))
})

const fetchMetadata = async () => {
  try {
    const response = await authGet(`/api/dataset/metadata_static/${props.datasetId}/`)
    rulerscale.value = response.scales || []
    
    if (rulerScales.value.length > 0 && !selectedScale.value) {
      selectedScale.value = rulerScales.value[0]
    }
  } catch (err) {
    console.error('Error fetching metadata:', err)
  }
}

const editScale = (scale, index) => {
  editingScale.value = index
  newScale.value = { ...scale }
}

const deleteScale = (index) => {
 
    rulerscale.value.splice(index, 1)
   
    saveScalesToBackend()
  
}

const saveScale = () => {
  if (editingScale.value !== null) {
    
    rulerscale.value[editingScale.value] = { ...newScale.value }
  } else {
    
    rulerscale.value.push({ ...newScale.value })
  }
  
  saveScalesToBackend()
  resetScaleForm()
}

const cancelEdit = () => {
  editingScale.value = null
  resetScaleForm()
}

const resetScaleForm = () => {
  newScale.value = {
    barcode: '',
    value_per_pixel: '',
    unit: 'µm'
  }
  editingScale.value = null
}

const saveScalesToBackend = async () => {
  try {
    const formdata = new FormData()
    formdata.append('scales', JSON.stringify(rulerscale.value))
    await authUpload(`/api/dataset/metadata_static/${props.datasetId}/`, 
      formdata
    )
  } catch (error) {
    console.error('Error saving scales:', error)
  }
}

const imageSettings = computed(() => ({
  opacity: annotationOpacity.value / 100,     
  brightness: imageBrightness.value / 100,     
  contrast: imageContrast.value / 100          
}))

const brushSettings = computed(() => ({
  size: brushSize.value
}))

if (props.annotationMode === 'detection') {
  activeTool.value = 'rectangle'
}
else {
  activeTool.value = 'brush'
}

const activeClass = ref(null)

const showClassDialog = ref(false)
const selectedClass = ref(null)
const classColor = ref('#1976D2')

const saveClass = () => {
  if (!selectedClass.value) return
  
  const className = typeof selectedClass.value === 'string' 
    ? selectedClass.value 
    : selectedClass.value.name
  
  if (!className) return

  const existingIndex = annotationClasses.value.findIndex(c => c.name === className)
  
  if (existingIndex !== -1) {
  
    annotationClasses.value[existingIndex].color = classColor.value
    

    if (activeClass.value?.name === className) {
      activeClass.value.color = classColor.value
    }
  } else {
   
    const newClass = {
      id: Date.now(),
      name: className,
      color: classColor.value
    }
    
    annotationClasses.value.push(newClass)
    activeClass.value = newClass
  }
  

  updateLabelProperties(annotationClasses.value)
  showClassDialog.value = false
}


const deleteClass = () => {
  if (!selectedClass.value || !selectedClass.value.id) return
  
  if (!confirm(`Удалить класс "${selectedClass.value.name}"?`)) return
  

  const updatedClasses = annotationClasses.value.filter(c => c.id !== selectedClass.value.id)
  annotationClasses.value = updatedClasses
  

  if (activeClass.value?.id === selectedClass.value.id) {
    activeClass.value = updatedClasses[0] || null
  }
  

  selectedClass.value = null
  classColor.value = '#1976D2'

  updateLabelProperties(updatedClasses)
  

  if (updatedClasses.length === 0) {
    showClassDialog.value = false
  }
}


const updateLabelProperties = async (classes) => {
  const newProperties = {}
  classes.forEach(classItem => {
    newProperties[classItem.name] = classItem.color
  })
  await sendClassesToBackend(newProperties)

}

const sendClassesToBackend = async (classesData) => {
  try {
    const response = await authPost(`/api/label_properties/${props.datasetId}/`, {
        label_properties: classesData,
    })
    
 
    return response
  } catch (error) {
  
  
    throw error
  }
}
const favoriteClasses = ref([])
const transformLabelProperties = (labelProperties) => {
  if (!labelProperties || typeof labelProperties !== 'object') {
    return []
  }
  if (props.favoriteClasses) {
    favoriteClasses.value = [...props.favoriteClasses]
  }
  console.log('favoriteClasses:', props.favoriteClasses)
  return Object.entries(labelProperties).map(([name, color], index) => ({
    id: index + 1,
    name: name,
    color: color,
    favorite: favoriteClasses.value.includes(name)
  }))
}
const sortedAnnotationClasses = computed(() => {
  if (!annotationClasses.value.length) return []
  

  return [...annotationClasses.value].sort((a, b) => {
    if (a.favorite && !b.favorite) return -1 
    if (!a.favorite && b.favorite) return 1   
    return a.name.localeCompare(b.name)       
  })
})
const toggleFavoriteClass = async (classItem) => {
  const className = classItem.name
  
  if (classItem.favorite) {
    
    favoriteClasses.value = favoriteClasses.value.filter(name => name !== className)
    classItem.favorite = false
  } else {
   
    favoriteClasses.value.push(className)
    classItem.favorite = true
  }
   const response = await authPost(`/api/label_properties/favorites/${props.datasetId}/`, {
        label_properties: favoriteClasses.value,
  } )
  
}
const annotationClasses = ref(transformLabelProperties(props.lableProperties))
watch(() => props.lableProperties, (newProps) => {
  annotationClasses.value = transformLabelProperties(newProps)
}, { immediate: true, deep: true })

watch(annotationClasses, (newClasses) => {
  if (newClasses.length > 0 && !activeClass.value) {
    activeClass.value = newClasses[0]
  }
}, { immediate: true })

watch(() => props.annotationMode, () => {
  if (props.annotationMode === 'detection' && activeTool.value === 'brush') {
    activeTool.value = 'rectangle'
  }
  else if (activeTool.value === 'rectangle') {
    activeTool.value = 'brush'
  }
}), { immediate: true }


const updateBrushSize = (newSize) => {
  brushSize.value = newSize
}


const setActiveTool = (tool) => {
  activeTool.value = tool
}

const setActiveClass = (cls) => {
  activeClass.value = cls
}
onMounted(() => {
  fetchMetadata()
})

defineExpose({
  activeTool,
  activeClass,
  annotationClasses,
  imageSettings,
  brushSettings,
  setActiveTool,
  setActiveClass, 
  updateBrushSize, 
  selectedScale
})
</script>

<style scoped>
.annotation-tools {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: rgb(var(--v-theme-surface));
}

.tools-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  background: rgba(var(--v-theme-on-surface), 0.02);
}

.tools-content {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
}
.scale-info {
  background: rgba(33, 150, 243, 0.05);
  border-radius: 8px;
  padding: 8px;
  border-left: 3px solid #2196f3;
}

.tool-section {
  margin-bottom: 20px;
}

.tool-buttons {
  display: grid;
  
  gap: 8px;
}

.tool-btn {
  height: 40px;
  font-size: 12px;
}

.classes-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.class-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.class-item:hover {
  background-color: rgba(var(--v-theme-primary), 0.04);
}

.class-item.active {
  background-color: rgba(var(--v-theme-primary), 0.08);
}

.class-name {
  font-size: 14px;
  color: rgba(var(--v-theme-on-surface));
}

.action-buttons {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
</style>
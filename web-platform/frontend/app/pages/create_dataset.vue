<template>
  <v-container fluid class="fill-height">
    <v-row justify="center" align="center">
      <v-col cols="12" md="8" lg="6" xl="5">
        <v-card class="pa-6 rounded-lg elevation-6 dataset-card">

          <v-card-title class="text-h4 font-weight-bold mb-4 text-center text-primary">
            <v-icon large class="mr-2" color="primary">mdi-database-plus</v-icon>
            {{ $t('create_dataset.title') }}
          </v-card-title>
          
          <v-divider class="mb-6"></v-divider>
          
          <v-form @submit.prevent="submitForm" ref="form">

            <v-row>
              <v-col cols="12">
                <v-text-field
                  v-model="formData.dataset_name"  
                  :label="getLabel('dataset_name')"  
                  :rules="[requiredRule]"  
                  variant="outlined"  
                  color="primary"  
                  prepend-inner-icon="mdi-rename-box" 
                  required  
                  clearable  
                ></v-text-field>
              </v-col>
              
              <v-col cols="12">
                <v-select
                  v-model="formData.access_type"
                  :items="policyTypes" 
                  item-title="name"  
                  item-value="id"  
                  :label="getLabel('access_type_name')"
                  :rules="[requiredRule]"
                  variant="outlined"
                  color="primary"
                  prepend-inner-icon="mdi-shield-account"
                  required
                ></v-select>
              </v-col>
            </v-row>

            <v-expansion-panels v-model="expansionPanel" class="my-4" multiple>
              
              <v-expansion-panel value="metadata">

                <v-expansion-panel-title expand-icon="mdi-chevron-down" collapse-icon="mdi-chevron-up">
                  <v-icon class="mr-2" color="secondary">mdi-tune</v-icon>
                  <span class="font-weight-medium">{{ $t('create_dataset.additional_fields') }}</span>
                </v-expansion-panel-title>
                
                <v-expansion-panel-text>
                  
                  <v-row v-for="(field, index) in metadata_static_fields" :key="index" class="mb-2">
                    <v-col cols="12">

                      <v-combobox
                        v-if="field.name !== 'asset_structure' && field.name !== 'scales'"
                        v-model="metadata_static[field.name]" 
                        :items="field.name === 'device_type_name' ? device_types : scaling_values"
                        item-title="name"
                        item-value="id"
                        :label="getLabel(field.name)"
                        variant="outlined"
                        color="primary"
                        clearable
                      ></v-combobox>

                      <v-text-field
                        v-else-if="field.name === 'asset_structure'"
                        v-model="metadata_static[field.name]"
                        :label="getLabel(field.name)"
                        variant="outlined"
                        color="primary"
                      ></v-text-field>

                      <div v-else-if="field.name === 'scales'">

                        <v-row v-for="(scale, sIndex) in metadata_static.scales" :key="sIndex" class="mb-2 align-center">

                          <v-col cols="3">
                            <v-text-field v-model="scale.barcode" label="Barcode" type="number" variant="outlined" />
                          </v-col>

                          <v-col cols="3">
                            <v-select v-model="scale.unit" :items="['nm','µm','mm','m']" label="Unit" variant="outlined" />
                          </v-col>

                          <v-col cols="3">
                            <v-text-field v-model="scale.value_per_pixel" label="Value per Pixel" type="number" variant="outlined" />
                          </v-col>

                          <v-col cols="3" class="d-flex align-center">
                            <v-btn icon color="red" @click="metadata_static.scales.splice(sIndex, 1)">
                              <v-icon>mdi-delete</v-icon>
                            </v-btn>
                          </v-col>

                        </v-row>

                        <v-btn color="primary" @click="metadata_static.scales.push({ barcode: 0, unit: 'nm', value_per_pixel: 0 })">
                          <v-icon left>mdi-plus</v-icon> Добавить шкалу
                        </v-btn>

                      </div>

                    </v-col>
                  </v-row>

                  <v-divider class="my-4"></v-divider>

                  <div class="mb-4">

                    <v-label class="text-subtitle-1 font-weight-medium mb-2 d-block">
                      <v-icon class="mr-1" small>mdi-label</v-icon>
                      {{ $t('create_dataset.label_properties') }}
                    </v-label>

                    <v-file-input
                      v-model="label_properties" 
                      :label="$t('create_dataset.label_properties_input')"
                      accept=".json,.yaml,.yml"  
                      variant="outlined"
                      color="primary"
                      prepend-icon="mdi-file-document"
                      :show-size="1000"  
                    ></v-file-input>

                  </div>

                  <v-divider class="my-4"></v-divider>

                  <div>
                    <v-label class="text-subtitle-1 font-weight-medium mb-3 d-block">
                      <v-icon class="mr-1" small>mdi-code-json</v-icon>
                      {{ $t('create_dataset.arbitrary_data') }}
                    </v-label>
                    
                    <v-alert v-if="Object.keys(arbitrary_data).length === 0" type="info" variant="tonal" class="mb-4">
                      {{ $t('create_dataset.no_custom_fields') }}
                    </v-alert>
                    
                    <div v-else>
                      <v-row v-for="(value, key, index) in arbitrary_data" :key="'arb_data_'+index" class="align-center mb-2">

                        <v-col cols="5">
                          <v-text-field
                            :model-value="key" 
                            :label="$t('create_dataset.field_name')"
                            variant="outlined"
                            readonly  
                          ></v-text-field>
                        </v-col>

                        <v-col cols="5">
                          <v-text-field
                            :model-value="value"
                            :label="$t('create_dataset.field_value')"
                            variant="outlined"
                            readonly
                          ></v-text-field>
                        </v-col>

                        <v-col cols="2" class="text-center">
                          <v-btn @click="removeField(key)" icon color="error" variant="text" size="small">
                            <v-icon>mdi-delete</v-icon>
                          </v-btn>
                        </v-col>

                      </v-row>
                    </div>

                    <v-dialog v-model="newFieldDialog" max-width="500">

                      <template v-slot:activator="{ props }">
                        <v-btn v-bind="props" color="secondary" variant="outlined" class="mt-2">
                          <v-icon left>mdi-plus</v-icon>
                          {{ $t('create_dataset.add_custom_field') }}
                        </v-btn>
                      </template>

                      <v-card>

                        <v-card-title class="text-h6">
                          {{ $t('create_dataset.new_custom_field') }}
                        </v-card-title>
                        
                        <v-card-text>
                          <v-text-field
                            v-model="newFieldName"
                            :label="$t('create_dataset.new_field_name')"
                            variant="outlined"
                            class="mb-3"
                          ></v-text-field>
                          
                          <v-text-field
                            v-model="newFieldValue"
                            :label="$t('create_dataset.new_field_value')"
                            variant="outlined"
                          ></v-text-field>
                        </v-card-text>
                        
                        <v-card-actions>
                          <v-spacer></v-spacer>

                          <v-btn @click="newFieldDialog = false" variant="text">
                            {{ $t('create_dataset.cancel') }}
                          </v-btn>

                          <v-btn @click="addCustomField" color="primary" :disabled="!newFieldName || !newFieldValue">
                            {{ $t('create_dataset.add') }}
                          </v-btn>

                        </v-card-actions>

                      </v-card>

                    </v-dialog>
                    
                  </div>

                </v-expansion-panel-text>

              </v-expansion-panel>
            </v-expansion-panels>

            <v-divider class="my-4"></v-divider>

            <v-row class="mt-4">
              
              <v-col cols="6">
                <v-btn 
                  @click="$router.push('/datasets')" 
                  variant="outlined" 
                  color="grey" 
                  block 
                  size="large"
                >
                  <v-icon left>mdi-arrow-left</v-icon>
                  {{ $t('create_dataset.cancel') }}
                </v-btn>
              </v-col>
              
              <v-col cols="6">
                <v-btn 
                  type="submit" 
                  color="primary" 
                  block 
                  size="large"
                  :loading="loading"  
                  :disabled="loading" 
                >
                  <v-icon left>mdi-check</v-icon>
                  {{ $t('create_dataset.create') }}
                </v-btn>
              </v-col>

            </v-row>
          </v-form>

          <v-snackbar v-model="successSnackbar" color="success" timeout="3000">
            {{ $t('create_dataset.success_message') }}
            <template v-slot:actions>
              <v-btn icon @click="successSnackbar = false">
                <v-icon>mdi-close</v-icon>
              </v-btn>
            </template>
          </v-snackbar>

          <v-snackbar v-model="errorSnackbar" color="error" timeout="5000">
            {{ error }}
            <template v-slot:actions>
              <v-btn icon @click="errorSnackbar = false">
                <v-icon>mdi-close</v-icon>
              </v-btn>
            </template>
          </v-snackbar>

        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>

definePageMeta({
  requiresAuth: true  
})
const { authGet, authPost } = useAuthFetch()
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const router = useRouter()

const loading = ref(false)  
const successSnackbar = ref(false)  
const errorSnackbar = ref(false)  
const error = ref('')  
const expansionPanel = ref([])  
const newFieldDialog = ref(false)  
const form = ref(null)  
const label_properties = ref(null)  
const device_types = ref([])  
const scaling_values = ref([])  
const arbitrary_data = reactive({})  
const metadata_static = reactive({})  
const policyTypes = ref([])  
const metadata_static_fields = ref([]) 
const formData = reactive({
  dataset_name: '',
  access_type: null,
})
const newFieldName = ref('')
const newFieldValue = ref('')

const requiredRule = value => !!value || t('create_dataset.required_field')

const getLabel = (field) => {
  return t(`create_dataset.${field}`)
}

const addCustomField = () => {
  if (newFieldName.value && newFieldValue.value) {
    arbitrary_data[newFieldName.value] = newFieldValue.value
    newFieldName.value = ''
    newFieldValue.value = ''
    newFieldDialog.value = false
  }
}

const removeField = (fieldName) => {
  delete arbitrary_data[fieldName]
}

const submitForm = async () => {
  const { valid } = await form.value.validate()
  
  if (!valid) {
    error.value = t('create_dataset.form_validation_error')
    errorSnackbar.value = true
    return
  }

  loading.value = true
  
  try {
    let processedMetadata = {}

    Object.entries(metadata_static).forEach(([key, value]) => {
      if (value !== '' && value !== null) {
        if (key.includes('_name')) {
          processedMetadata[key.replace('_name', '')] = { [key]: value }
        } else {
          processedMetadata[key] = value
        }
      }
    })
    
    if (Object.keys(arbitrary_data).length > 0) {
      processedMetadata.arbitrary_data = arbitrary_data
    }

    const metadataStaticValue = Object.keys(processedMetadata).length > 0 
      ? JSON.stringify(processedMetadata) 
      : null

    const submitData = new FormData()
    submitData.append('dataset_name', formData.dataset_name)
    submitData.append('access_type', formData.access_type)
    
    if (metadataStaticValue) {
      submitData.append('metadata_static', metadataStaticValue)
    }
    
    if (label_properties.value) {
      submitData.append('label_properties', label_properties.value)
    }

    await authPost('/api/datasets/', submitData, {
      headers: {
        'Accept': 'application/json'
      }
    })

    successSnackbar.value = true
    setTimeout(() => {
      router.push('/datasets')
    }, 1500)
    
  } catch (err) {
    error.value = err.data?.message || t('create_dataset.unknown_error')
    errorSnackbar.value = true
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  try {
    const response = await authGet('/api/tables/')
    const { Access_Type, Device_Type, Metadata_Static, Scaling_Value } = response

    metadata_static_fields.value = [
      ...Scaling_Value.fields.map(field => ({ name: field, isCustom: false })),
      ...Device_Type.fields.map(field => ({ name: field, isCustom: false })),
      ...Metadata_Static.fields.map(field => ({ name: field, isCustom: false })),
    ]

    metadata_static_fields.value.forEach(field => {
      metadata_static[field.name] = ''
    })

    metadata_static['scales'] = []
    device_types.value = Device_Type.device_types.map(t => ({ id: t.id, name: t.name }))
    scaling_values.value = Scaling_Value.scaling_values.map(t => ({ id: t.id, name: t.name }))
    policyTypes.value = Access_Type.access_types.map(t => ({ id: t.id, name: t.name }))

  } catch (err) {
    error.value = t('create_dataset.data_load_error')
    errorSnackbar.value = true
  }
})

</script>

<style scoped>
.dataset-card {
  backdrop-filter: blur(10px);
  background: rgba(var(--v-theme-surface), 0.92); 
}

:deep(.v-expansion-panel-title__overlay) {
  opacity: 0.1;
}

:deep(.v-field__outline) {
  border-radius: 8px;
}

/* @media (max-width: 960px) {
  .dataset-card {
    margin: 16px;
    padding: 20px;
  }
} */

.text-primary {
  color: rgb(var(--v-theme-primary));
}
</style>
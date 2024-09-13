import UTemplate from './UTemplate.vue'

import Button from 'primevue/button'
import Calendar from 'primevue/calendar'
import InputNumber from 'primevue/inputnumber'
import RadioButton from 'primevue/radiobutton'
import Checkbox from 'primevue/checkbox'
import InputText from 'primevue/inputtext'
import FloatLabel from 'primevue/floatlabel'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import ProgressBar from 'primevue/progressbar'
import Dialog from 'primevue/dialog'
import Textarea from 'primevue/textarea'
import Skeleton from 'primevue/skeleton'
import ConfirmDialog from 'primevue/confirmdialog'
import Password from 'primevue/password'
import FileUpload from 'primevue/fileupload'

const components = [
  {
    name: 'UTemplate',
    component: UTemplate
  },
  {
    name: 'Button',
    component: Button
  },
  {
    name: 'Calendar',
    component: Calendar
  },
  {
    name: 'InputNumber',
    component: InputNumber
  },
  {
    name: 'RadioButton',
    component: RadioButton
  },
  {
    name: 'Checkbox',
    component: Checkbox
  },
  {
    name: 'InputText',
    component: InputText
  },
  {
    name: 'FloatLabel',
    component: FloatLabel
  },
  {
    name: 'DataTable',
    component: DataTable
  },
  {
    name: 'Column',
    component: Column
  },
  {
    name: 'ProgressBar',
    component: ProgressBar
  },
  {
    name: 'Dialog',
    component: Dialog
  },
  {
    name: 'TextArea',
    component: Textarea
  },
  {
    name: 'Skeleton',
    component: Skeleton
  },
  {
    name: 'ConfirmDialog',
    component: ConfirmDialog
  },
  {
    name: 'Password',
    component: Password
  },
  {
    name: 'FileUpload',
    component: FileUpload
  }
]

export default {
  install(app) {
    components.forEach(({ name, component }) => {
      app.component(name, component)
    })
  }
}

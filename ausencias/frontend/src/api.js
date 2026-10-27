// Cliente HTTP único: injeta o JWT e converte erros da API em mensagens em português.
const BASE = '/api'
let token = localStorage.getItem('token')

export const setToken = (t) => {
  token = t
  t ? localStorage.setItem('token', t) : localStorage.removeItem('token')
}

async function request(path, { method = 'GET', body, form } = {}) {
  const headers = {}
  if (token) headers.Authorization = `Bearer ${token}`
  if (body) headers['Content-Type'] = 'application/json'
  let res
  try {
    res = await fetch(BASE + path, { method, headers, body: form || (body ? JSON.stringify(body) : undefined) })
  } catch {
    throw new Error('Não foi possível conectar ao servidor. Verifique se o backend está rodando (uvicorn).')
  }
  if (res.status === 401 && token) {
    setToken(null)
    window.dispatchEvent(new Event('session-expired'))
  }
  if (!res.ok) {
    let msg = 'Erro inesperado.'
    try {
      const j = await res.json()
      msg = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail)
    } catch {}
    throw new Error(msg)
  }
  return res.status === 204 ? null : res.json()
}

export const api = {
  get: (p) => request(p),
  post: (p, body) => request(p, { method: 'POST', body: body ?? {} }),
  put: (p, body) => request(p, { method: 'PUT', body }),
  upload: (p, file) => {
    const f = new FormData()
    f.append('file', file)
    return request(p, { method: 'POST', form: f })
  },
}

// Baixa/abre arquivos protegidos (PDF, CSV, anexo) enviando o token no cabeçalho.
export async function download(path, filename, openInTab = false) {
  const win = openInTab ? window.open('', '_blank') : null
  const res = await fetch(BASE + path, { headers: { Authorization: `Bearer ${token}` } })
  if (!res.ok) {
    win?.close()
    let msg = 'Falha ao gerar o arquivo.'
    try { msg = (await res.json()).detail || msg } catch {}
    throw new Error(msg)
  }
  const url = URL.createObjectURL(await res.blob())
  if (win) win.location = url
  else {
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
  }
}

export const fmtDate = (iso) => (iso ? new Date(iso + 'T00:00:00').toLocaleDateString('pt-BR') : '-')
export const fmtDT = (iso) => (iso ? new Date(iso).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : '-')
export const fmtHours = (h) => (h == null ? '—' : h >= 48 ? `${(h / 24).toFixed(1)} dias` : `${h} h`)

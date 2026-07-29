"""Scripts embutíveis no site institucional (widget de formulário e beacon de
rastreio) — servidos como JavaScript puro, sem dependências, pra colar direto
no HTML de qualquer site (item 9.8)."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.form import FORM_FIELD_LIBRARY, FORM_FIELD_TYPES, Form
from app.repositories.form import FormRepository

router = APIRouter(prefix="/embed", tags=["Scripts embutíveis"])


@router.get("/track.js")
def track_script():
    js = """
(function () {
  var tag = document.currentScript;
  var tenantId = tag.getAttribute('data-tenant-id');
  if (!tenantId) return;
  var base = tag.src.replace(/\\/embed\\/track\\.js.*$/, '');
  var key = 'gdc_session_id';
  var sessionId = sessionStorage.getItem(key);
  if (!sessionId) {
    sessionId = Date.now().toString(36) + Math.random().toString(36).slice(2);
    sessionStorage.setItem(key, sessionId);
  }
  fetch(base + '/public/track', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      tenant_id: tenantId, session_id: sessionId,
      path: location.pathname, referrer: document.referrer || null,
    }),
    keepalive: true,
  }).catch(function () {});
})();
"""
    return Response(content=js, media_type="application/javascript")


@router.get("/form.js")
def form_script(form_id: str = Query(...)):
    js = FORM_WIDGET_JS.replace("__FORM_ID__", form_id)
    return Response(content=js, media_type="application/javascript")


@router.get("/forms/{form_id}/config")
def form_config(form_id: UUID, db: Session = Depends(get_db)):
    """Config pública e segura (só nome + campos) pro widget montar o HTML do formulário."""
    form = FormRepository(db).get_public(form_id)
    if form is None or form.status != "ativo":
        raise HTTPException(status_code=404, detail="Formulário não encontrado ou inativo")
    return {
        "nome": form.nome,
        "campos": [
            {
                "key": c,
                "label": FORM_FIELD_LIBRARY.get(c) or form.campos_personalizados.get(c, c),
                "tipo": FORM_FIELD_TYPES.get(c, "text"),
            }
            for c in form.campos
        ],
    }


FORM_WIDGET_JS = """
(function () {
  var tag = document.currentScript;
  var formId = '__FORM_ID__';
  var base = tag.src.replace(/\\/embed\\/form\\.js.*$/, '');

  function el(tag, attrs, children) {
    var e = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    (children || []).forEach(function (c) { e.appendChild(c); });
    return e;
  }

  fetch(base + '/embed/forms/' + formId + '/config').then(function (r) {
    if (!r.ok) throw new Error('form indisponível');
    return r.json();
  }).then(function (config) {
    var form = document.createElement('form');
    form.className = 'gdc-form';

    function field(name, label, tipo) {
      var wrap = el('div', { style: 'margin-bottom:12px;' });
      wrap.appendChild(el('label', { style: 'display:block;font-size:13px;font-weight:600;margin-bottom:4px;' }, [document.createTextNode(label)]));
      var inputStyle = 'width:100%;padding:8px;border:1px solid #ccc;border-radius:6px;box-sizing:border-box;';
      var input;
      if (tipo === 'boolean') {
        input = el('select', { name: name, style: inputStyle });
        [['', 'Selecione'], ['Sim', 'Sim'], ['Não', 'Não']].forEach(function (pair) {
          var opt = document.createElement('option');
          opt.value = pair[0];
          opt.textContent = pair[1];
          input.appendChild(opt);
        });
      } else {
        input = el(tipo === 'textarea' ? 'textarea' : 'input', { name: name, style: inputStyle });
        if (tipo && tipo !== 'textarea') input.setAttribute('type', tipo);
      }
      wrap.appendChild(input);
      return wrap;
    }

    form.appendChild(field('nome', 'Nome', 'text'));
    form.appendChild(field('email', 'E-mail', 'email'));
    config.campos.forEach(function (c) {
      form.appendChild(field(c.key, c.label, c.tipo || 'text'));
    });

    var submitBtn = el('button', { type: 'submit', style: 'background:#2D3561;color:#fff;border:none;padding:10px 18px;border-radius:6px;cursor:pointer;font-weight:600;' }, [document.createTextNode('Enviar')]);
    form.appendChild(submitBtn);

    var msg = el('p', { style: 'display:none;margin-top:10px;font-size:13px;' });
    form.appendChild(msg);

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var data = new FormData(form);
      var nome = data.get('nome'), email = data.get('email');
      var valores = {};
      config.campos.forEach(function (c) { var v = data.get(c.key); if (v) valores[c.key] = v; });
      fetch(base + '/public/forms/' + formId + '/submit', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nome: nome, email: email, valores: valores }),
      }).then(function (r) {
        msg.style.display = 'block';
        if (r.ok) {
          msg.style.color = '#0ca30c';
          msg.textContent = 'Obrigado! Entraremos em contato em breve.';
          form.reset();
        } else {
          msg.style.color = '#d03b3b';
          msg.textContent = 'Não foi possível enviar. Tente novamente.';
        }
      }).catch(function () {
        msg.style.display = 'block';
        msg.style.color = '#d03b3b';
        msg.textContent = 'Não foi possível enviar. Tente novamente.';
      });
    });

    tag.parentNode.insertBefore(form, tag);
  }).catch(function () {});
})();
"""

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

  // Injeta o CSS uma única vez por página, mesmo com vários formulários embutidos.
  // font-family: inherit deliberadamente — o widget herda a tipografia do site
  // hospedeiro em vez de trazer a própria (mantém "sem dependências").
  if (!document.getElementById('gdc-form-styles')) {
    var style = document.createElement('style');
    style.id = 'gdc-form-styles';
    style.textContent = ''
      + '.gdc-form{font-family:inherit;}'
      + '.gdc-form .gdc-field{margin-bottom:16px;}'
      + '.gdc-form label{display:block;font-size:13px;font-weight:600;margin-bottom:6px;color:inherit;}'
      + '.gdc-form input,.gdc-form select,.gdc-form textarea{'
      +   'width:100%;padding:10px 12px;border:1px solid #D8D8D2;border-radius:3px;'
      +   'box-sizing:border-box;font:inherit;font-size:14px;color:inherit;background:#fff;'
      +   'transition:border-color .15s ease,box-shadow .15s ease;}'
      + '.gdc-form textarea{min-height:88px;resize:vertical;}'
      + '.gdc-form input:focus,.gdc-form select:focus,.gdc-form textarea:focus{'
      +   'outline:2px solid #D9B654;outline-offset:1px;border-color:#2B2F5E;}'
      + '.gdc-form-submit{'
      +   'width:100%;background:#2B2F5E;color:#fff;border:none;padding:12px 20px;'
      +   'border-radius:3px;cursor:pointer;font:inherit;font-size:14px;font-weight:600;'
      +   'transition:background-color .15s ease;}'
      + '.gdc-form-submit:hover{background:#3A3F78;}'
      + '.gdc-form-submit:disabled{opacity:.6;cursor:default;}'
      + '.gdc-form-msg{display:none;margin-top:14px;padding:10px 14px;border-radius:6px;font-size:13px;}'
      + '.gdc-form-msg.ok{display:block;background:#E4F1EA;color:#2E7D5B;}'
      + '.gdc-form-msg.err{display:block;background:#F8E7E5;color:#B4453C;}';
    document.head.appendChild(style);
  }

  fetch(base + '/embed/forms/' + formId + '/config').then(function (r) {
    if (!r.ok) throw new Error('form indisponível');
    return r.json();
  }).then(function (config) {
    var form = document.createElement('form');
    form.className = 'gdc-form';

    function field(name, label, tipo) {
      var wrap = el('div', { class: 'gdc-field' });
      wrap.appendChild(el('label', {}, [document.createTextNode(label)]));
      var input;
      if (tipo === 'boolean') {
        input = el('select', { name: name });
        [['', 'Selecione'], ['Sim', 'Sim'], ['Não', 'Não']].forEach(function (pair) {
          var opt = document.createElement('option');
          opt.value = pair[0];
          opt.textContent = pair[1];
          input.appendChild(opt);
        });
      } else {
        input = el(tipo === 'textarea' ? 'textarea' : 'input', { name: name });
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

    var submitBtn = el('button', { type: 'submit', class: 'gdc-form-submit' }, [document.createTextNode('Enviar')]);
    form.appendChild(submitBtn);

    var msg = el('p', { class: 'gdc-form-msg' });
    form.appendChild(msg);

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var data = new FormData(form);
      var nome = data.get('nome'), email = data.get('email');
      var valores = {};
      config.campos.forEach(function (c) { var v = data.get(c.key); if (v) valores[c.key] = v; });
      submitBtn.disabled = true;
      fetch(base + '/public/forms/' + formId + '/submit', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nome: nome, email: email, valores: valores }),
      }).then(function (r) {
        submitBtn.disabled = false;
        if (r.ok) {
          msg.className = 'gdc-form-msg ok';
          msg.textContent = 'Obrigado! Entraremos em contato em breve.';
          form.reset();
        } else {
          msg.className = 'gdc-form-msg err';
          msg.textContent = 'Não foi possível enviar. Tente novamente.';
        }
      }).catch(function () {
        submitBtn.disabled = false;
        msg.className = 'gdc-form-msg err';
        msg.textContent = 'Não foi possível enviar. Tente novamente.';
      });
    });

    tag.parentNode.insertBefore(form, tag);
  }).catch(function () {});
})();
"""

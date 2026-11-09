// Export every Claude Project of your organization (instructions, knowledge docs, uploaded files as base64).
// Run in a Chrome tab on https://claude.ai/api/organizations (a plain JSON page that does not reload).
// Progress lives in window.__exp; when done it downloads claude-projects-export-<date>.json.
// If your account belongs to several organizations, set window.__ORG = '<org uuid>' before running this.
window.__exp = {done: false, n: 0, total: 0, err: null, missing: [], projects: []};
(async () => {
  const toBase64 = async (blob) => {
    const buf = new Uint8Array(await blob.arrayBuffer());
    let s = '';
    for (let i = 0; i < buf.length; i += 0x8000) s += String.fromCharCode.apply(null, buf.subarray(i, i + 0x8000));
    return btoa(s);
  };
  try {
    const orgs = await fetch('/api/organizations').then(r => r.json());
    const chosen = window.__ORG ? orgs.find(o => o.uuid === window.__ORG) : (orgs.length === 1 ? orgs[0] : null);
    if (!chosen) throw new Error(window.__ORG ? `organization ${window.__ORG} not found`
      : `this account has ${orgs.length} organizations; set window.__ORG to one of: ${orgs.map(o => `${o.uuid} (${o.name})`).join(', ')}`);
    const org = chosen.uuid;
    const list = await fetch(`/api/organizations/${org}/projects?limit=500`).then(r => r.json());
    window.__exp.total = list.length;
    for (const p of list) {
      const base = `/api/organizations/${org}/projects/${p.uuid}`;
      const [detail, docs, files] = await Promise.all([base, base + '/docs', base + '/files'].map(u => fetch(u).then(r => r.json())));
      const outFiles = [];
      for (const f of files) {
        // Originals first (PDFs), then guessed raw-content routes, then the preview (images).
        const candidates = [];
        if (f.document_asset?.url) candidates.push([f.document_asset.url, 'original']);
        candidates.push([`/api/${org}/files/${f.file_uuid}/contents`, 'contents'], [`/api/organizations/${org}/files/${f.file_uuid}/content`, 'content']);
        if (f.preview_asset?.url) candidates.push([f.preview_asset.url, 'preview']);
        let got = null;
        for (const [url, variant] of candidates) {
          try {
            const r = await fetch(url);
            const ct = r.headers.get('content-type') || '';
            if (r.ok && !ct.includes('json') && !ct.includes('html')) { got = {variant, contentType: ct, data: await toBase64(await r.blob())}; break; }
          } catch (e) {}
        }
        if (!got) window.__exp.missing.push(`${p.name} :: ${f.file_name}`);
        outFiles.push({file_uuid: f.file_uuid, file_name: f.file_name, file_kind: f.file_kind, size_bytes: f.size_bytes, created_at: f.created_at, ...(got || {variant: null})});
      }
      window.__exp.projects.push({uuid: p.uuid, name: p.name, description: detail.description, is_private: detail.is_private,
        creator: detail.creator?.full_name, created_at: detail.created_at, updated_at: detail.updated_at,
        prompt_template: detail.prompt_template,
        docs: docs.map(d => ({uuid: d.uuid, file_name: d.file_name, created_at: d.created_at, content: d.content})),
        files: outFiles});
      window.__exp.n++;
    }
    const payload = JSON.stringify({exportedAt: new Date().toISOString(), organization: {uuid: org, name: chosen.name},
      missing: window.__exp.missing, projects: window.__exp.projects});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([payload], {type: 'application/json'}));
    a.download = `claude-projects-export-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(a);
    a.click();
  } catch (e) { window.__exp.err = String(e); }
  window.__exp.done = true;
})();
'started';

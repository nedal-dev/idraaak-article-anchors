" Uses a local Python child process. No shell, network or buffer writes.
let s:worker = expand('<sfile>:p:h:h') . '/python/check_article.py'
let s:requests = {}
let s:serial = 0
let s:limit = 2097152

function! s:message(text, error) abort
  if a:error
    echohl WarningMsg
  endif
  echom '[Idraaak Anchors] ' . a:text
  echohl None
endfunction

function! s:python() abort
  if exists('g:idraaak_anchors_python')
    return type(g:idraaak_anchors_python) == v:t_list ? copy(g:idraaak_anchors_python) : [g:idraaak_anchors_python]
  endif
  for l:cmd in (has('win32') || has('win64') ? [['py', '-3'], ['python3'], ['python']] : [['python3'], ['python']])
    if executable(l:cmd[0])
      return l:cmd
    endif
  endfor
  return []
endfunction

function! s:clear_list(buf) abort
  let l:id = getbufvar(a:buf, 'idraaak_anchors_qfid', 0)
  if l:id > 0
    let l:qf = getqflist({'id': l:id, 'context': 1})
    if get(l:qf, 'id', 0) == l:id && type(get(l:qf, 'context', 0)) == v:t_dict && get(l:qf.context, 'owner', '') == 'idraaak-anchors'
      call setqflist([], 'r', {'id': l:id, 'items': [], 'title': 'Idraaak Anchors: cleared'})
    endif
  endif
endfunction

function! s:cancel(buf) abort
  let l:key = string(a:buf)
  if has_key(s:requests, l:key)
    let l:state = remove(s:requests, l:key)
    call timer_stop(l:state.timer)
    if has_key(l:state, 'job') && job_status(l:state.job) == 'run'
      call job_stop(l:state.job)
    endif
  endif
  call setbufvar(a:buf, 'idraaak_anchors_pending', 0)
endfunction

function! idraaak_anchors#clear(buf) abort
  call s:cancel(a:buf)
  call s:clear_list(a:buf)
  call setbufvar(a:buf, 'idraaak_anchors_report', {})
endfunction

function! idraaak_anchors#invalidate(buf) abort
  if getbufvar(a:buf, 'idraaak_anchors_pending', 0) || !empty(getbufvar(a:buf, 'idraaak_anchors_report', {}))
    call idraaak_anchors#clear(a:buf)
  endif
endfunction

function! s:active(state) abort
  return has_key(s:requests, a:state.key) && s:requests[a:state.key].serial == a:state.serial
endfunction

function! s:output(state, channel, message) abort
  if s:active(a:state)
    call add(a:state.output, a:message)
  endif
endfunction

function! s:error(state, channel, message) abort
  if s:active(a:state) && strlen(a:state.error) < 4096
    let a:state.error .= a:message . ' '
  endif
endfunction

function! s:timeout(state, timer) abort
  if s:active(a:state)
    call s:cancel(a:state.buf)
    call s:message('Check timed out; no results applied.', 1)
  endif
endfunction

function! s:closed(state, channel) abort
  if !s:active(a:state)
    return
  endif
  call remove(s:requests, a:state.key)
  call timer_stop(a:state.timer)
  if !bufexists(a:state.buf)
    return
  endif
  call setbufvar(a:state.buf, 'idraaak_anchors_pending', 0)
  if getbufvar(a:state.buf, 'changedtick') != a:state.tick
    call s:message('Buffer changed; discarded old results. Run the check again.', 0)
    return
  endif
  try
    let l:report = json_decode(join(a:state.output, "\n"))
    if type(l:report) != v:t_dict || !get(l:report, 'ok', 0)
      throw get(l:report, 'error', 'No valid report from Python.')
    endif
  catch
    call setbufvar(a:state.buf, 'idraaak_anchors_report', {})
    call s:message('Could not run the checker. Verify Python 3.8+ and :help idraaak-anchors-python. ' . (empty(a:state.error) ? v:exception : a:state.error), 1)
    return
  endtry
  let l:items = []
  for l:issue in l:report.issues
    call add(l:items, {'bufnr': a:state.buf, 'lnum': l:issue.line, 'col': l:issue.column,
          \ 'text': l:issue.message, 'type': l:issue.kind == 'base_href' ? 'W' : 'E'})
  endfor
  call setqflist([], ' ', {'title': 'Idraaak Article Anchors', 'items': l:items,
        \ 'context': {'owner': 'idraaak-anchors', 'bufnr': a:state.buf, 'changedtick': a:state.tick}})
  call setbufvar(a:state.buf, 'idraaak_anchors_qfid', getqflist({'id': 0}).id)
  call setbufvar(a:state.buf, 'idraaak_anchors_report', l:report)
  call s:message(printf('%d issue(s); %d fragment link(s) checked; %d skipped. Use :copen or :cnext.%s',
        \ len(l:items), l:report.links_checked, l:report.links_skipped,
        \ l:report.truncated ? ' Showing the first 500 issues.' : ''), 0)
endfunction

function! idraaak_anchors#check() abort
  if has('nvim') || !has('job') || !has('channel') || !has('timers') || !exists('*json_encode')
    call s:message('Requires Vim 8.2+ with +job, +channel and +timers. Neovim is not supported.', 1)
    return
  endif
  if &encoding !=# 'utf-8'
    call s:message('Set encoding=utf-8 before checking Arabic/Unicode article source.', 1)
    return
  endif
  let l:command = s:python()
  if empty(l:command) || type(l:command[0]) != v:t_string || !executable(l:command[0])
    call s:message('Python was not found. Set g:idraaak_anchors_python; see :help idraaak-anchors-python.', 1)
    return
  endif
  let l:source = join(getline(1, '$'), "\n")
  if strlen(l:source) > s:limit
    call s:message('The buffer is larger than 2 MiB; check a smaller article.', 1)
    return
  endif
  call idraaak_anchors#clear(bufnr('%'))
  let s:serial += 1
  let l:state = {'buf': bufnr('%'), 'key': string(bufnr('%')), 'tick': b:changedtick,
        \ 'serial': s:serial, 'output': [], 'error': ''}
  let s:requests[l:state.key] = l:state
  let b:idraaak_anchors_pending = 1
  let l:state.timer = timer_start(20000, function('s:timeout', [l:state]))
  try
    let l:state.job = job_start(l:command + ['-I', '-B', s:worker], {
          \ 'in_io': 'pipe', 'out_io': 'pipe', 'err_io': 'pipe', 'out_mode': 'nl', 'err_mode': 'nl',
          \ 'out_cb': function('s:output', [l:state]), 'err_cb': function('s:error', [l:state]),
          \ 'close_cb': function('s:closed', [l:state]), 'stoponexit': 'term'})
    if job_status(l:state.job) == 'fail'
      throw 'Python process could not start.'
    endif
    call ch_sendraw(job_getchannel(l:state.job), json_encode({'source': l:source}) . "\n")
    call ch_close_in(job_getchannel(l:state.job))
  catch
    call s:cancel(l:state.buf)
    call s:message('Could not start Python: ' . v:exception, 1)
  endtry
endfunction

/* TutorLoreto AI · PMV1 · Frontend M3E sin dependencias externas */
'use strict';
const VISTAS = new Set(['portada','login','cambiar_contrasena','cuentas','inicio','asignaturas','biblioteca','consulta','registro','procesando','explicacion','validacion','ayuda','conexion','error_ia','sin_lan','sin_resultados','limite','desempeno','perfil','practica','historial']);
const NAV = new Set(['inicio','asignaturas','biblioteca','consulta','ayuda']);
const PUBLICAS = new Set(['portada','login','ayuda']);
const $ = id => document.getElementById(id);
function obtenerPerfilId(){
  try{
    let id=localStorage.getItem('tutorloreto.perfil-id');
    if(!id){
      if(globalThis.crypto?.randomUUID)id=crypto.randomUUID();
      else if(globalThis.crypto?.getRandomValues){
        const bytes=crypto.getRandomValues(new Uint8Array(16));
        bytes[6]=(bytes[6]&0x0f)|0x40;bytes[8]=(bytes[8]&0x3f)|0x80;
        const hex=[...bytes].map(b=>b.toString(16).padStart(2,'0')).join('');
        id=`${hex.slice(0,8)}-${hex.slice(8,12)}-${hex.slice(12,16)}-${hex.slice(16,20)}-${hex.slice(20)}`;
      }else id='xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g,c=>{const r=Math.random()*16|0;return(c==='x'?r:(r&3|8)).toString(16);});
      localStorage.setItem('tutorloreto.perfil-id',id);
    }
    return id;
  }catch{return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g,c=>{const r=Math.random()*16|0;return(c==='x'?r:(r&3|8)).toString(16);});}
}
const state = {asignaturas:[], seleccionada:null, pregunta:'', consultaId:null, respuesta:null, cargando:false, catalogoError:false, vista:'portada', perfilId:null, grado:null, practicaId:null, temaPendiente:'', asignaturaPendiente:null, bibliotecaCursoId:null, bibliotecaTemaId:null, bibliotecaPractica:null, bibliotecaGradoFiltro:null, usuario:null, authReady:false};
const emojis = {'matematica':'📐','comunicacion':'📖','ciencia y tecnologia':'🔬','ciencias sociales':'🌎','desarrollo personal, ciudadania y civica':'🤝','educacion para el trabajo':'🛠️','ingles':'🗣️','arte y cultura':'🎨','educacion fisica':'⚽','educacion religiosa':'📜','castellano como segunda lengua':'💬'};
const extra = ['📖','✍️','🔬','🌎','🎨'];
const normalizar = valor => String(valor || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('es-PE');
const emojiDe = (materia,i=0) => emojis[normalizar(materia.nombre)] || extra[i%extra.length];
function poner(id,valor){$(id).textContent=String(valor);}
function decir(mensaje){poner('notificaciones',mensaje);}
function ir(vista, {historial=true}={}){
  if(!VISTAS.has(vista))vista='portada';
  if(state.authReady){
    if(!state.usuario&&!PUBLICAS.has(vista))vista='login';
    if(state.usuario){
      if(state.usuario.debe_cambiar_contrasena&&!['cambiar_contrasena','ayuda'].includes(vista))vista='cambiar_contrasena';
      else if(['portada','login'].includes(vista))vista=state.usuario.rol==='alumno'?'inicio':'cuentas';
      else if(state.usuario.rol!=='alumno'&&!['cuentas','cambiar_contrasena','ayuda'].includes(vista))vista='cuentas';
      else if(state.usuario.rol==='alumno'&&vista==='cuentas')vista='inicio';
    }
  }
  state.vista=vista;
  document.querySelectorAll('[data-vista]').forEach(el=>{el.hidden=el.dataset.vista!==vista;});
  $('nav-inferior').hidden=!NAV.has(vista);
  document.querySelectorAll('[data-nav]').forEach(el=>el.dataset.nav===vista?el.setAttribute('aria-current','page'):el.removeAttribute('aria-current'));
  if(historial && location.hash.slice(1)!==vista)history.pushState({vista},'',`#${vista}`);
  if(vista==='consulta')refrescarConsulta();
  if(vista==='asignaturas')mostrarAsignaturas();
  if(vista==='biblioteca')mostrarBibliotecaCursos();
  if(vista==='conexion')comprobarConexion();
  if(vista==='perfil')prepararPerfil();
  if(vista==='practica')prepararPractica();
  if(vista==='historial')cargarSeguimiento();
  if(vista==='cuentas')cargarCuentas();
  if(vista==='cambiar_contrasena')prepararCambioContrasena();
  window.scrollTo(0,0);
  const encabezado=$(`vista-${vista}`)?.querySelector('h1');
  if(encabezado){encabezado.tabIndex=-1;encabezado.focus({preventScroll:true});}
  decir(`Pantalla: ${encabezado?.textContent || vista}`);
}
function nombreActual(){return state.asignaturas.find(a=>a.id===state.seleccionada)?.nombre || 'Sin seleccionar';}
function elegir(id, continuar=false){
  if(!state.asignaturas.some(a=>a.id===id))return;
  state.seleccionada=id;mostrarAsignaturas();mostrarDestacados();refrescarConsulta();
  decir(`Asignatura seleccionada: ${nombreActual()}`);
  if(continuar)ir('consulta');
}
function mostrarDestacados(){
  const caja=$('cursos-destacados');caja.replaceChildren();
  if(!state.asignaturas.length){const p=document.createElement('p');p.className='texto-ayuda';p.textContent=state.catalogoError?'Error de MySQL: revisa la conexión desde Áreas.':'Todavía no hay asignaturas registradas.';caja.append(p);return;}
  state.asignaturas.slice(0,4).forEach((materia,i)=>{
    const btn=document.createElement('button');btn.type='button';btn.className='curso-destacado';
    const em=document.createElement('span');em.textContent=emojiDe(materia,i);em.setAttribute('aria-hidden','true');
    const nombre=document.createElement('strong');nombre.textContent=materia.nombre;btn.append(em,nombre);
    btn.addEventListener('click',()=>elegir(materia.id,true));caja.append(btn);
  });
}
function mostrarAsignaturas(){
  const caja=$('lista-asignaturas');caja.replaceChildren();
  const q=normalizar($('buscar-asignatura').value.trim());
  const lista=state.asignaturas.filter(a=>normalizar(a.nombre).includes(q));
  poner('contador-asignaturas',`${lista.length} ${lista.length===1?'asignatura':'asignaturas'} ${q?'encontradas':'disponibles'}`);
  $('continuar-asignatura').disabled=state.seleccionada===null;
  $('error-asignaturas').hidden=!state.catalogoError;
  lista.forEach((materia,i)=>{
    const btn=document.createElement('button');btn.type='button';btn.className='curso-entrada';btn.setAttribute('aria-pressed',String(state.seleccionada===materia.id));
    const em=document.createElement('span');em.className='icono-area';em.textContent=emojiDe(materia,i);em.setAttribute('aria-hidden','true');
    const nombre=document.createElement('span');const titulo=document.createElement('strong');titulo.textContent=materia.nombre;
    const sub=document.createElement('small');sub.textContent='Área curricular';nombre.append(titulo,sub);
    const marca=document.createElement('span');marca.className='marca';marca.textContent=state.seleccionada===materia.id?'✓':'›';marca.setAttribute('aria-hidden','true');
    btn.append(em,nombre,marca);btn.addEventListener('click',()=>elegir(materia.id));caja.append(btn);
  });
  if(q && !lista.length && !state.catalogoError && state.vista==='asignaturas'){
    poner('busqueda-sin-resultado',$('buscar-asignatura').value);ir('sin_resultados');
  }
}
function temasDelCurso(materia){
  const catalogo=window.TUTORLORETO_BIBLIOTECA||{};
  return catalogo[normalizar(materia?.nombre)]||[];
}
function cambiarPanelBiblioteca(panel){
  $('biblioteca-cursos').hidden=panel!=='cursos';
  $('biblioteca-temas').hidden=panel!=='temas';
  $('biblioteca-detalle-tema').hidden=panel!=='detalle';
}
function mostrarBibliotecaCursos(){
  cambiarPanelBiblioteca('cursos');
  const lista=$('biblioteca-lista-cursos');lista.replaceChildren();
  const busqueda=normalizar($('biblioteca-buscar-curso').value.trim());
  const cursos=state.asignaturas.filter(materia=>normalizar(materia.nombre).includes(busqueda));
  const totalTemas=state.asignaturas.reduce((total,materia)=>total+temasDelCurso(materia).length,0);
  poner('biblioteca-total-cursos',state.asignaturas.length);
  poner('biblioteca-cursos-resumen',`${cursos.length} cursos · ${totalTemas} temas con teoría y práctica local`);
  $('biblioteca-sin-cursos').hidden=state.asignaturas.length>0;
  $('biblioteca-sin-resultados-cursos').hidden=state.asignaturas.length===0||cursos.length>0;
  cursos.forEach((materia,i)=>{
    const temas=temasDelCurso(materia);
    const boton=document.createElement('button');boton.type='button';boton.className='biblioteca-curso-card';
    const cabecera=document.createElement('span');cabecera.className='biblioteca-curso-card-cabecera';
    const icono=document.createElement('span');icono.className='biblioteca-curso-icono';icono.textContent=emojiDe(materia,i);icono.setAttribute('aria-hidden','true');
    const marca=document.createElement('span');marca.className='biblioteca-curso-flecha';marca.textContent='↗';marca.setAttribute('aria-hidden','true');
    cabecera.append(icono,marca);
    const titulo=document.createElement('strong');titulo.className='biblioteca-curso-nombre';titulo.textContent=materia.nombre;
    const competencia=temas[0]?.competencia||'Explora los temas de esta área curricular.';
    const descripcion=document.createElement('small');descripcion.className='biblioteca-curso-descripcion';descripcion.textContent=competencia;
    const pie=document.createElement('span');pie.className='biblioteca-curso-pie';
    const cantidad=document.createElement('span');cantidad.textContent=`${temas.length} temas`;
    const grados=document.createElement('span');grados.textContent=temas.length?'1.° a 5.°':'Por completar';
    pie.append(cantidad,grados);boton.append(cabecera,titulo,descripcion,pie);boton.addEventListener('click',()=>{
      state.bibliotecaCursoId=materia.id;
      state.bibliotecaGradoFiltro=state.grado?'mi-grado':'todos';
      $('biblioteca-buscar-tema').value='';
      mostrarBibliotecaTemas();
    });
    lista.append(boton);
  });
}
function mostrarBibliotecaTemas(){
  const materia=state.asignaturas.find(item=>item.id===state.bibliotecaCursoId);
  if(!materia){mostrarBibliotecaCursos();return;}
  cambiarPanelBiblioteca('temas');
  poner('biblioteca-nombre-curso',materia.nombre);
  const temas=temasDelCurso(materia);
  poner('biblioteca-competencia-curso',temas[0]?.competencia||'Temas de aprendizaje para secundaria.');
  if(state.bibliotecaGradoFiltro===null)state.bibliotecaGradoFiltro=state.grado?String(state.grado):'todos';
  const selector=$('biblioteca-filtro-grado');
  selector.value=state.bibliotecaGradoFiltro;
  if(selector.value!==state.bibliotecaGradoFiltro){state.bibliotecaGradoFiltro='todos';selector.value='todos';}
  const gradoFiltro=selector.value==='mi-grado'?(state.grado?String(state.grado):'todos'):selector.value;
  const busqueda=normalizar($('biblioteca-buscar-tema').value.trim());
  const visibles=temas.filter(tema=>
    (gradoFiltro==='todos'||String(tema.grado||1)===gradoFiltro) &&
    (!busqueda||normalizar(`${tema.tema} ${tema.unidad||''} ${tema.competencia||''}`).includes(busqueda))
  );
  poner('biblioteca-resumen-temas',`${temas.length} temas · 4 por grado. Cada tema incluye teoría y práctica local; el video opcional requiere Internet. Ruta vinculada a competencias del CNEB, adaptable a la programación de tu colegio.`);
  poner('biblioteca-conteo-temas',`${visibles.length} de ${temas.length} temas${gradoFiltro==='todos'?' · todos los grados':` · ${gradoFiltro}.° de secundaria`}`);
  $('biblioteca-temas-pendientes').hidden=temas.length>0;
  $('biblioteca-sin-resultados-temas').hidden=visibles.length>0||temas.length===0;
  const lista=$('biblioteca-lista-temas');lista.replaceChildren();
  const grupos=new Map();
  visibles.forEach(tema=>{
    const clave=`${tema.grado||1}|${tema.unidad||'Temas del curso'}`;
    if(!grupos.has(clave))grupos.set(clave,[]);
    grupos.get(clave).push(tema);
  });
  let numero=0;
  for(const [clave,lecciones] of grupos){
    const [grado,unidad]=clave.split('|');
    const modulo=document.createElement('section');modulo.className='biblioteca-modulo';
    const cabecera=document.createElement('div');cabecera.className='biblioteca-modulo-cabecera';
    const tituloModulo=document.createElement('h3');tituloModulo.textContent=unidad;
    const etiqueta=document.createElement('span');etiqueta.className='biblioteca-grado-etiqueta';etiqueta.textContent=`${grado}.° secundaria`;
    cabecera.append(tituloModulo,etiqueta);modulo.append(cabecera);
    const items=document.createElement('div');items.className='biblioteca-modulo-lecciones';
    lecciones.forEach(tema=>{
      numero++;
      const boton=document.createElement('button');boton.type='button';boton.className='biblioteca-leccion';
      const indice=document.createElement('span');indice.className='biblioteca-leccion-numero';indice.textContent=String(numero).padStart(2,'0');
      const contenido=document.createElement('span');contenido.className='biblioteca-leccion-contenido';
      const titulo=document.createElement('strong');titulo.textContent=tema.tema;
      const detalle=document.createElement('small');detalle.textContent='📖 Teoría local  ·  ✍️ Práctica  ·  ▶ Video opcional';
      contenido.append(titulo,detalle);
      const flecha=document.createElement('span');flecha.className='biblioteca-leccion-flecha';flecha.textContent='›';flecha.setAttribute('aria-hidden','true');
      boton.append(indice,contenido,flecha);boton.addEventListener('click',()=>abrirTemaBiblioteca(tema.id));items.append(boton);
    });
    modulo.append(items);lista.append(modulo);
  }
}
function abrirTemaBiblioteca(temaId){
  const materia=state.asignaturas.find(item=>item.id===state.bibliotecaCursoId);
  const tema=temasDelCurso(materia).find(item=>item.id===temaId);
  if(!materia||!tema)return;
  state.bibliotecaTemaId=tema.id;state.bibliotecaPractica=tema.practica;
  cambiarPanelBiblioteca('detalle');
  const gradoTema=Number(tema.grado||state.grado);
  $('biblioteca-etiqueta-curso').textContent=`${materia.nombre} · ${Number.isInteger(gradoTema)&&gradoTema>0?`${gradoTema}.° secundaria`:'Secundaria'}`;
  poner('biblioteca-titulo-tema',tema.tema);
  poner('biblioteca-competencia-tema',`${tema.unidad||'Módulo de aprendizaje'} · ${tema.competencia||'Aprendizaje para secundaria'}`);
  const teoria=$('biblioteca-teoria');teoria.replaceChildren();
  tema.teoria.forEach(bloque=>{
    const seccion=document.createElement('section');seccion.className='biblioteca-bloque-teoria';
    const titulo=document.createElement('h3');titulo.textContent=bloque.titulo;
    const texto=document.createElement('p');texto.textContent=bloque.texto;
    seccion.append(titulo,texto);teoria.append(seccion);
  });
  poner('biblioteca-enunciado-practica',tema.practica.enunciado);
  const form=$('form-biblioteca-respuesta');form.reset();
  const opciones=$('biblioteca-opciones-practica');opciones.replaceChildren();
  const leyenda=document.createElement('legend');leyenda.textContent='Elige una alternativa';opciones.append(leyenda);
  tema.practica.opciones.forEach((texto,indice)=>{
    const etiqueta=document.createElement('label');etiqueta.className='opcion-practica';
    const radio=document.createElement('input');radio.type='radio';radio.name='biblioteca-opcion';radio.value=String(indice);radio.required=true;
    const contenido=document.createElement('span');contenido.textContent=texto;
    etiqueta.append(radio,contenido);opciones.append(etiqueta);
    radio.addEventListener('change',()=>{$('biblioteca-enviar-respuesta').disabled=false;});
  });
  $('biblioteca-enviar-respuesta').disabled=true;
  $('biblioteca-resultado-practica').hidden=true;
  $('biblioteca-resultado-practica').classList.remove('respuesta-correcta','respuesta-incorrecta');
  $('biblioteca-mensaje-practica').replaceChildren();
  const busqueda=`${tema.video||tema.tema} ${materia.nombre} secundaria`;
  const enlace=$('biblioteca-enlace-video');
  enlace.href=`https://www.youtube.com/results?search_query=${encodeURIComponent(busqueda)}`;
  enlace.setAttribute('aria-label',`Buscar videos de ${tema.tema} en YouTube; requiere internet`);
}
function practicarTemaBiblioteca(temaId=state.bibliotecaTemaId){
  const materia=state.asignaturas.find(item=>item.id===state.bibliotecaCursoId);
  const tema=temasDelCurso(materia).find(item=>item.id===temaId);
  if(!materia||!tema)return;
  state.temaPendiente=tema.tema;state.asignaturaPendiente=materia.id;ir('practica');
}
async function enviarPracticaBiblioteca(evento){
  evento.preventDefault();
  const opcion=$('form-biblioteca-respuesta').querySelector('input[name="biblioteca-opcion"]:checked');
  const materia=state.asignaturas.find(item=>item.id===state.bibliotecaCursoId);
  const tema=temasDelCurso(materia).find(item=>item.id===state.bibliotecaTemaId);
  if(!opcion||!materia||!tema||!state.bibliotecaPractica)return;
  if(!state.grado){
    const aviso=$('biblioteca-mensaje-practica');aviso.replaceChildren();
    const texto=document.createElement('p');texto.textContent='Guarda tu grado para registrar esta respuesta en Mi progreso.';
    const boton=document.createElement('button');boton.type='button';boton.className='btn btn-secundario';boton.dataset.ir='perfil';boton.textContent='Configurar mi grado';
    aviso.append(texto,boton);return;
  }
  const boton=$('biblioteca-enviar-respuesta');boton.disabled=true;
  $('biblioteca-mensaje-practica').textContent='Guardando tu respuesta…';
  try{
    const resultado=await pedir('/api/practicas/biblioteca',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        perfil_id:state.perfilId,asignatura_id:materia.id,tema:tema.tema,
        enunciado:state.bibliotecaPractica.enunciado,
        opciones:state.bibliotecaPractica.opciones,
        respuesta_correcta:state.bibliotecaPractica.respuesta_correcta,
        explicacion:state.bibliotecaPractica.explicacion,opcion:Number(opcion.value)
      })
    });
    mostrarResultadoBiblioteca(resultado.correcta,resultado.respuesta_correcta,resultado.explicacion);
    $('biblioteca-mensaje-practica').textContent='Tu respuesta quedó guardada en Mi progreso.';
  }catch(error){
    const correcta=Number(opcion.value)===state.bibliotecaPractica.respuesta_correcta;
    mostrarResultadoBiblioteca(correcta,state.bibliotecaPractica.opciones[state.bibliotecaPractica.respuesta_correcta],state.bibliotecaPractica.explicacion);
    $('biblioteca-mensaje-practica').textContent=`Se revisó en este dispositivo, pero no se guardó en Mi progreso: ${error.mensaje||'el servidor escolar no respondió.'}`;
  }
  $('biblioteca-opciones-practica').querySelectorAll('input').forEach(input=>{input.disabled=true;});
}
function mostrarResultadoBiblioteca(correcta,respuesta,explicacion){
  poner('biblioteca-resultado-titulo',correcta?'¡Muy bien, es correcto!':'Vamos a revisar el error');
  $('biblioteca-resultado-practica').classList.toggle('respuesta-correcta',Boolean(correcta));
  $('biblioteca-resultado-practica').classList.toggle('respuesta-incorrecta',!correcta);
  poner('biblioteca-respuesta-correcta',respuesta);poner('biblioteca-explicacion-practica',explicacion);
  $('biblioteca-resultado-practica').hidden=false;
}
function refrescarConsulta(){
  poner('curso-consulta',nombreActual());
  if($('pregunta').value!==state.pregunta)$('pregunta').value=state.pregunta;
  actualizarContador();
}
function actualizarGradoResumen(){
  poner('grado-resumen',state.grado?`${state.grado}.° de secundaria`:'Configura tu nivel');
  poner('practica-grado',state.grado?`${state.grado}.° de secundaria`:'Sin registrar');
}
function prepararPerfil(){
  const perfilColegio=state.usuario?.rol==='alumno';
  $('perfil-asignado-colegio').hidden=!perfilColegio;
  $('form-perfil').hidden=perfilColegio;
  $('perfil-grado').value=state.grado?String(state.grado):'';
  poner('perfil-grado-asignado',state.grado?`${state.grado}.° de secundaria`:'Sin grado asignado. Consulta con el colegio.');
}
async function cargarPerfil(){
  try{
    const perfil=await pedir(`/api/perfiles/${encodeURIComponent(state.perfilId)}`);
    state.grado=Number(perfil.grado);
    if(!Number.isInteger(state.grado)||state.grado<1||state.grado>5)state.grado=null;
  }catch(error){
    if(error.http!==404){poner('perfil-mensaje',error.mensaje||'No se pudo cargar tu perfil.');}
  }
  actualizarGradoResumen();
  if(state.vista==='perfil')prepararPerfil();
  if(state.vista==='practica')prepararPractica();
  if(state.vista==='historial')cargarSeguimiento();
}
async function guardarPerfil(evento){
  evento.preventDefault();
  const boton=evento.currentTarget.querySelector('button[type="submit"]');
  boton.disabled=true;poner('perfil-mensaje','Guardando tu grado…');
  try{
    const perfil=await pedir(`/api/perfiles/${encodeURIComponent(state.perfilId)}`,{
      method:'PUT',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({grado:Number($('perfil-grado').value)})
    });
    state.grado=Number(perfil.grado);actualizarGradoResumen();
    poner('perfil-mensaje','Grado guardado. Las explicaciones y ejercicios se ajustarán a tu nivel.');
    decir('Perfil de aprendizaje guardado');
  }catch(error){poner('perfil-mensaje',error.mensaje||'No se pudo guardar el grado.');}
  finally{boton.disabled=false;}
}
function actualizarAsignaturasPractica(){
  const selector=$('practica-asignatura');
  const actual=Number(selector.value)||state.asignaturaPendiente||state.seleccionada;
  selector.replaceChildren();
  const inicial=document.createElement('option');inicial.value='';inicial.textContent='Selecciona un área';selector.append(inicial);
  state.asignaturas.forEach(materia=>{
    const opcion=document.createElement('option');opcion.value=String(materia.id);opcion.textContent=materia.nombre;selector.append(opcion);
  });
  if(actual!==null&&state.asignaturas.some(m=>m.id===actual))selector.value=String(actual);
}
function prepararPractica(){
  actualizarGradoResumen();actualizarAsignaturasPractica();
  const faltaPerfil=!state.grado;
  $('practica-perfil-requerido').hidden=!faltaPerfil;
  $('form-practica').hidden=faltaPerfil;
  if(state.temaPendiente){$('practica-tema').value=state.temaPendiente;state.temaPendiente='';state.practicaId=null;$('ejercicio-generado').hidden=true;}
  if(state.asignaturaPendiente!==null){$('practica-asignatura').value=String(state.asignaturaPendiente);state.asignaturaPendiente=null;}
}
async function crearPractica(evento){
  evento.preventDefault();
  if(!state.grado){poner('perfil-mensaje','Registra tu grado para crear un ejercicio adaptado.');ir('perfil');return;}
  const boton=$('generar-practica');
  const tema=$('practica-tema').value.trim();
  const asignaturaId=Number($('practica-asignatura').value);
  if(!asignaturaId||tema.length<2){poner('practica-mensaje','Selecciona una asignatura y escribe un tema.');return;}
  boton.disabled=true;$('ejercicio-generado').hidden=true;poner('practica-mensaje','La IA está preparando un ejercicio…');state.practicaId=null;
  try{
    const ejercicio=await pedir('/api/practicas/generar',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({perfil_id:state.perfilId,asignatura_id:asignaturaId,tema,dificultad:$('practica-dificultad').value})
    });
    state.practicaId=ejercicio.id;
    poner('ejercicio-etiqueta',`${ejercicio.asignatura} · ${ejercicio.tema} · ${ejercicio.dificultad}`);
    poner('ejercicio-enunciado',ejercicio.enunciado);
    const opciones=$('opciones-practica');opciones.replaceChildren();
    const leyenda=document.createElement('legend');leyenda.textContent='Elige una alternativa';opciones.append(leyenda);
    ejercicio.opciones.forEach((texto,indice)=>{
      const etiqueta=document.createElement('label');etiqueta.className='opcion-practica';
      const radio=document.createElement('input');radio.type='radio';radio.name='opcion';radio.value=String(indice);radio.required=true;
      const contenido=document.createElement('span');contenido.textContent=texto;
      etiqueta.append(radio,contenido);opciones.append(etiqueta);
      radio.addEventListener('change',()=>{$('enviar-respuesta-practica').disabled=false;});
    });
    $('enviar-respuesta-practica').disabled=true;$('resultado-practica').hidden=true;$('otra-practica').hidden=true;
    $('ejercicio-generado').hidden=false;poner('practica-mensaje','Ejercicio listo. Tu respuesta se guardará en tu historial.');
  }catch(error){poner('practica-mensaje',error.mensaje||'No se pudo generar el ejercicio. Comprueba Ollama y MySQL.');}
  finally{boton.disabled=false;}
}
async function revisarPractica(evento){
  evento.preventDefault();
  const opcion=$('form-respuesta-practica').querySelector('input[name="opcion"]:checked');
  if(!state.practicaId||!opcion)return;
  const boton=$('enviar-respuesta-practica');boton.disabled=true;
  try{
    const resultado=await pedir(`/api/practicas/${encodeURIComponent(state.practicaId)}/respuesta`,{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({perfil_id:state.perfilId,opcion:Number(opcion.value)})
    });
    poner('resultado-practica-titulo',resultado.correcta?'¡Muy bien, es correcto!':'Vamos a revisar el error');
    $('resultado-practica').classList.toggle('respuesta-correcta',Boolean(resultado.correcta));
    $('resultado-practica').classList.toggle('respuesta-incorrecta',!resultado.correcta);
    poner('respuesta-practica-correcta',resultado.respuesta_correcta);
    poner('explicacion-practica',resultado.explicacion);
    $('resultado-practica').hidden=false;$('otra-practica').hidden=false;
    $('opciones-practica').querySelectorAll('input').forEach(input=>{input.disabled=true;});
    poner('practica-mensaje',resultado.repetida?'Se mostró la respuesta que ya estaba guardada.':'Tu respuesta se agregó al historial.');
    decir(resultado.correcta?'Respuesta correcta':'Respuesta incorrecta; revisa la explicación');
  }catch(error){poner('practica-mensaje',error.mensaje||'No se pudo revisar la respuesta.');boton.disabled=false;}
}
function nuevaPractica(){
  state.practicaId=null;$('ejercicio-generado').hidden=true;$('resultado-practica').hidden=true;$('otra-practica').hidden=true;
  $('practica-tema').value='';poner('practica-mensaje','Escribe el siguiente tema que quieres practicar.');
  $('practica-tema').focus();
}
function actualizarContador(){
  const n=$('pregunta').value.length;poner('contador-pregunta',`${n} / 2000`);
  $('contador-pregunta').classList.toggle('exceso',n>2000);
}
async function pedir(url,options={}){
  let respuesta;
  try{respuesta=await fetch(url,{cache:'no-store',...options});}
  catch(e){throw {red:true,mensaje:'No se pudo contactar el servidor escolar.'};}
  let contenido;try{contenido=await respuesta.json();}catch{contenido={};}
  if(!respuesta.ok)throw {http:respuesta.status,mensaje:typeof contenido.detail==='string'?contenido.detail:`Error HTTP ${respuesta.status}.`};
  return contenido;
}
function aplicarUsuario(usuario){
  state.usuario=usuario;
  state.perfilId=usuario.rol==='alumno'?usuario.perfil_id:null;
  state.grado=usuario.rol==='alumno'?Number(usuario.grado)||null:null;
  actualizarGradoResumen();
  if($('inicio-correo'))$('inicio-correo').textContent=usuario.correo;
  if($('cuentas-correo-actual'))$('cuentas-correo-actual').textContent=usuario.correo;
  if($('cuentas-rol-actual'))$('cuentas-rol-actual').textContent=usuario.rol==='directivo'?'Directivo':'Docente';
}
async function autenticar(evento){
  evento.preventDefault();
  const boton=$('login-enviar');boton.disabled=true;poner('login-mensaje','Comprobando tu cuenta…');
  try{
    const datos=await pedir('/api/auth/login',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({correo:$('login-correo').value.trim(),contrasena:$('login-contrasena').value})
    });
    aplicarUsuario(datos.usuario);state.authReady=true;$('login-contrasena').value='';
    if(datos.usuario.rol==='alumno')await cargarAsignaturas();
    ir(datos.usuario.debe_cambiar_contrasena?'cambiar_contrasena':datos.usuario.rol==='alumno'?'inicio':'cuentas');
  }catch(error){poner('login-mensaje',error.mensaje||'No se pudo iniciar sesión. Revisa tus datos o consulta al colegio.');}
  finally{boton.disabled=false;}
}
async function comprobarSesion(){
  try{
    const datos=await pedir('/api/auth/me');
    aplicarUsuario(datos.usuario);state.authReady=true;
    if(datos.usuario.rol==='alumno')await cargarAsignaturas();
    ir(datos.usuario.debe_cambiar_contrasena?'cambiar_contrasena':datos.usuario.rol==='alumno'?'inicio':'cuentas',{historial:false});
  }catch{
    state.usuario=null;state.perfilId=null;state.grado=null;state.authReady=true;
    ir('portada',{historial:false});
  }
}
function prepararCambioContrasena(){
  poner('contrasena-indicacion',state.usuario?.debe_cambiar_contrasena?
    'Por seguridad, cambia la contraseña temporal para continuar.':
    'Puedes actualizar la contraseña de tu cuenta cuando lo necesites.');
  $('form-cambiar-contrasena').reset();$('contrasena-mensaje').textContent='';
}
async function guardarContrasena(evento){
  evento.preventDefault();
  const nueva=$('contrasena-nueva').value;
  if(nueva!==$('contrasena-confirmar').value){poner('contrasena-mensaje','Las nuevas contraseñas no coinciden.');return;}
  const boton=evento.currentTarget.querySelector('button[type="submit"]');boton.disabled=true;
  poner('contrasena-mensaje','Actualizando contraseña…');
  try{
    await pedir('/api/auth/contrasena',{
      method:'PUT',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({contrasena_actual:$('contrasena-actual').value,contrasena_nueva:nueva})
    });
    state.usuario.debe_cambiar_contrasena=false;
    poner('contrasena-mensaje','Contraseña actualizada.');
    ir(state.usuario.rol==='alumno'?'inicio':'cuentas');
  }catch(error){poner('contrasena-mensaje',error.mensaje||'No se pudo cambiar la contraseña.');}
  finally{boton.disabled=false;}
}
async function cerrarSesion(){
  try{await pedir('/api/auth/logout',{method:'POST'});}
  catch(error){decir(error.mensaje||'No se pudo cerrar la sesión con el servidor.');return;}
  state.usuario=null;state.perfilId=null;state.grado=null;state.authReady=true;
  state.asignaturas=[];state.seleccionada=null;ir('portada');
}
function actualizarFormularioCuenta(){
  const select=$('cuenta-rol');
  const opcionDocente=select.querySelector('option[value="docente"]');
  const esDirectivo=state.usuario?.rol==='directivo';
  opcionDocente.hidden=!esDirectivo;
  if(!esDirectivo&&select.value==='docente')select.value='alumno';
  const esAlumno=select.value==='alumno';
  $('cuenta-campos-alumno').hidden=!esAlumno;
  $('cuenta-grado').required=esAlumno;
  $('cuenta-vigencia').required=esAlumno;
}
async function cargarCuentas(){
  if(!state.usuario||!['directivo','docente'].includes(state.usuario.rol))return;
  actualizarFormularioCuenta();
  const lista=$('lista-cuentas');lista.replaceChildren();
  try{
    const datos=await pedir('/api/auth/cuentas');
    $('cuentas-vacio').hidden=datos.cuentas.length>0;
    datos.cuentas.forEach(cuenta=>{
      const tarjeta=document.createElement('article');tarjeta.className='cuenta-fila';
      const info=document.createElement('div');
      const correo=document.createElement('strong');correo.textContent=cuenta.correo;
      const detalle=document.createElement('small');
      const rol=cuenta.rol==='alumno'?`Alumno · ${cuenta.grado}.°`:(cuenta.rol==='directivo'?'Directivo':'Docente');
      const vencimiento=cuenta.vigente_hasta?` · Vigente hasta ${cuenta.vigente_hasta}`:' · Sin vencimiento';
      detalle.textContent=`${rol}${vencimiento} · ${cuenta.activo?'Activa':'Desactivada'}`;
      info.append(correo,detalle);tarjeta.append(info);
      if(cuenta.rol==='alumno'&&cuenta.activo){
        const boton=document.createElement('button');boton.type='button';boton.className='btn btn-texto btn-pequeno';
        boton.dataset.desactivarCuenta=cuenta.id;boton.textContent='Desactivar';
        boton.setAttribute('aria-label',`Desactivar la cuenta de ${cuenta.correo}`);tarjeta.append(boton);
      }
      lista.append(tarjeta);
    });
  }catch(error){poner('cuenta-mensaje',error.mensaje||'No se pudo consultar la lista de cuentas.');}
}
async function crearCuentaEscolar(evento){
  evento.preventDefault();
  const rol=$('cuenta-rol').value;
  const correo=$('cuenta-correo').value.trim();
  const contrasena=$('cuenta-contrasena').value;
  const carga={correo,contrasena_temporal:contrasena,rol};
  if(rol==='alumno'){
    carga.grado=Number($('cuenta-grado').value);
    carga.vigente_hasta=$('cuenta-vigencia').value;
  }
  const boton=evento.currentTarget.querySelector('button[type="submit"]');boton.disabled=true;
  poner('cuenta-mensaje','Creando la cuenta…');
  try{
    const datos=await pedir('/api/auth/cuentas',{
      method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(carga)
    });
    evento.currentTarget.reset();actualizarFormularioCuenta();
    poner('cuenta-mensaje',`Cuenta ${datos.cuenta.rol} creada para ${datos.cuenta.correo}. Entrégale el correo y la contraseña temporal al usuario.`);
    await cargarCuentas();
  }catch(error){poner('cuenta-mensaje',error.mensaje||'No se pudo crear la cuenta.');}
  finally{boton.disabled=false;}
}
async function desactivarCuenta(usuarioId){
  if(!confirm('¿Desactivar esta cuenta de alumno? Ya no podrá iniciar sesión.'))return;
  try{
    await pedir(`/api/auth/cuentas/${encodeURIComponent(usuarioId)}/desactivar`,{method:'POST'});
    poner('cuenta-mensaje','La cuenta quedó desactivada.');await cargarCuentas();
  }catch(error){poner('cuenta-mensaje',error.mensaje||'No se pudo desactivar la cuenta.');}
}
async function cargarAsignaturas(){
  try{
    const lista=await pedir('/api/asignaturas');
    if(!Array.isArray(lista))throw {mensaje:'Respuesta incorrecta del catálogo.'};
    state.asignaturas=lista.filter(a=>Number.isInteger(a.id)&&typeof a.nombre==='string');state.catalogoError=false;
    if(state.seleccionada!==null && !state.asignaturas.some(a=>a.id===state.seleccionada))state.seleccionada=null;
  }catch(e){state.catalogoError=true;state.asignaturas=[];decir(e.mensaje||'No se pudo cargar el catálogo');}
  mostrarDestacados();mostrarAsignaturas();refrescarConsulta();actualizarAsignaturasPractica();
  if(state.vista==='biblioteca')mostrarBibliotecaCursos();
  if(state.vista==='practica')prepararPractica();
}
async function guardarConsulta(){
  if(state.cargando)return;
  state.pregunta=$('pregunta').value;
  if(state.seleccionada===null){poner('mensaje-validacion','Debes seleccionar una asignatura antes de enviar.');ir('validacion');return;}
  if(!state.pregunta.trim()){poner('mensaje-validacion','Escribe una pregunta para que tu tutor pueda ayudarte.');ir('validacion');return;}
  if(state.pregunta.length>2000){poner('longitud-pregunta',state.pregunta.length);ir('limite');return;}
  state.cargando=true;$('enviar').disabled=true;
  try{
    const dato=await pedir('/api/consultas',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({asignatura_id:state.seleccionada,pregunta:state.pregunta.trim(),perfil_id:state.grado?state.perfilId:null})});
    state.consultaId=dato.id;state.respuesta=null;poner('registro-id',`#${dato.id}`);poner('registro-resumen',state.pregunta.trim());ir('registro');
  }catch(e){
    if(e.red)ir('sin_lan');
    else{poner('mensaje-validacion',e.mensaje||'No se pudo guardar la consulta.');ir('validacion');}
  }finally{state.cargando=false;$('enviar').disabled=false;}
}
function mostrarExplicacion(contenido){
  const caja=$('explicacion-pasos');caja.replaceChildren();
  // Respeta íntegramente el texto de Ollama. Solo divide párrafos para facilitar lectura.
  const porParrafos=String(contenido||'').trim().split(/\n\s*\n+/).filter(Boolean);
  const partes=porParrafos.length>1?porParrafos:String(contenido||'').trim().split(/\n(?=\s*(?:\d+[).:-]|paso\s+\d+))/i).filter(Boolean);
  partes.forEach((fragmento,i)=>{
    const bloque=document.createElement('article');bloque.className='paso-respuesta';
    const n=document.createElement('span');n.className='paso-numero';n.textContent=String(i+1).padStart(2,'0');
    
    const texto = document.createElement('div');
    const p = document.createElement('p');

    fragmento.split(/(\*\*[^*]+\*\*)/g).forEach(parte => {
      if (parte.startsWith('**') && parte.endsWith('**')) {
        const negrita = document.createElement('strong');
        negrita.textContent = parte.slice(2, -2);
        p.append(negrita);
      } else {
        p.append(document.createTextNode(parte));
      }
    });

    texto.append(p);
    bloque.append(n, texto);
    caja.append(bloque);

  });
}
async function generarExplicacion(){
  if(state.cargando||!state.consultaId)return;
  state.cargando=true;ir('procesando');
  try{
    const respuesta=await pedir(`/api/consultas/${encodeURIComponent(state.consultaId)}/explicacion`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({perfil_id:state.grado?state.perfilId:null})});
    state.respuesta=respuesta;poner('curso-explicacion',nombreActual());poner('pregunta-explicacion',state.pregunta);
    mostrarExplicacion(respuesta.contenido);
    
if (typeof renderMathInElement === "function") {
  renderMathInElement(document.getElementById("explicacion-pasos"), {
    delimiters: [
      { left: "$$", right: "$$", display: true },
      { left: "\\[", right: "\\]", display: true },
      { left: "\\(", right: "\\)", display: false }
    ],
    throwOnError: false
  });
}
    ir('explicacion');
  }catch(e){poner('detalle-error-ia',e.mensaje||'No fue posible generar la explicación con la IA configurada.');ir('error_ia');}
  finally{state.cargando=false;}
}
function nuevaPregunta(){state.pregunta='';state.consultaId=null;state.respuesta=null;$('pregunta').value='';actualizarContador();ir('consulta');}
async function comprobarConexion(){
  poner('estado-servidor','Comprobando…');poner('estado-modelo','Comprobando…');
  let disponible=false;
  try{await pedir('/api/estado');poner('estado-servidor','Disponible');disponible=true;}
  catch{poner('estado-servidor','Sin respuesta');}
  if(disponible){
    try{const dato=await pedir('/api/ia/estado');poner('estado-modelo',dato.disponible?'Listo':'No disponible');poner('detalle-conexion',dato.detalle||`Modelo: ${dato.modelo||'no informado'}`);}
    catch{poner('estado-modelo','Sin comprobar');poner('detalle-conexion','El servidor responde pero no se pudo comprobar Ollama.');}
  }else{poner('estado-modelo','Sin comprobar');poner('detalle-conexion','Comprueba FastAPI, la dirección y la red escolar.');}
}
function mostrarProgreso(datos){
  poner('resumen-practicas',datos.total_practicas||0);
  poner('resumen-aciertos',`${Number(datos.porcentaje_aciertos||0)}%`);
  poner('resumen-consultas',datos.total_consultas||0);
  const caja=$('lista-progreso');caja.replaceChildren();
  const temas=Array.isArray(datos.temas)?datos.temas:[];
  $('progreso-vacio').hidden=temas.length>0;
  temas.forEach(item=>{
    const tarjeta=document.createElement('article');tarjeta.className='tema-progreso';
    const titulo=document.createElement('h3');titulo.textContent=`${item.asignatura} · ${item.tema}`;
    const resumen=document.createElement('p');resumen.textContent=`${item.aciertos} de ${item.intentos} respuestas correctas · ${item.porcentaje_aciertos}%`;
    const barra=document.createElement('div');barra.className='barra-progreso';barra.setAttribute('role','progressbar');barra.setAttribute('aria-label',`Aciertos en ${item.tema}`);barra.setAttribute('aria-valuemin','0');barra.setAttribute('aria-valuemax','100');barra.setAttribute('aria-valuenow',String(item.porcentaje_aciertos));
    const valor=document.createElement('span');valor.style.width=`${Math.max(0,Math.min(100,Number(item.porcentaje_aciertos)||0))}%`;barra.append(valor);
    const boton=document.createElement('button');boton.type='button';boton.className='enlace';boton.textContent='Practicar este tema →';boton.dataset.practicar=item.tema;boton.dataset.asignatura=String(item.asignatura_id);
    tarjeta.append(titulo,resumen,barra,boton);caja.append(tarjeta);
  });
}
function mostrarHistorial(actividades){
  const caja=$('lista-historial');caja.replaceChildren();
  const lista=Array.isArray(actividades)?actividades:[];
  $('historial-vacio').hidden=lista.length>0;
  lista.forEach(item=>{
    const tarjeta=document.createElement('article');tarjeta.className='actividad-historial';
    const cabecera=document.createElement('div');cabecera.className='actividad-cabecera';
    const tipo=document.createElement('strong');tipo.textContent=item.tipo==='practica'?'Práctica':'Consulta';
    const fecha=document.createElement('time');fecha.textContent=formatearFecha(item.creado_en);if(item.creado_en)fecha.dateTime=item.creado_en;
    cabecera.append(tipo,fecha);
    const materia=document.createElement('p');materia.className='actividad-materia';materia.textContent=item.tema?`${item.asignatura} · ${item.tema}`:item.asignatura;
    const detalle=document.createElement('p');detalle.className='actividad-detalle';detalle.textContent=item.detalle||'';
    const explicacion=document.createElement('p');explicacion.className='actividad-detalle';
    if(item.tipo==='practica'&&item.respuesta_elegida)explicacion.textContent=`Tu respuesta: ${item.respuesta_elegida} · Correcta: ${item.respuesta_correcta}`;
    if(item.explicacion)explicacion.textContent+=(explicacion.textContent?'\n':'')+`Explicación: ${item.explicacion}`;
    const estado=document.createElement('span');estado.className='chip '+(item.estado==='ACIERTO'?'chip-exito':item.estado==='PARA_REFORZAR'?'chip-alerta':'chip-neutro');
    estado.textContent=item.estado==='ACIERTO'?'Correcta':item.estado==='PARA_REFORZAR'?'Para reforzar':item.estado==='PENDIENTE'?'Pendiente':item.estado;
    tarjeta.append(cabecera,materia,detalle,estado);
    if(explicacion.textContent)tarjeta.append(explicacion);
    caja.append(tarjeta);
  });
}
function formatearFecha(valor){
  if(!valor)return 'Fecha no disponible';
  const fecha=new Date(valor);
  return Number.isNaN(fecha.getTime())?'Fecha no disponible':new Intl.DateTimeFormat('es-PE',{dateStyle:'medium',timeStyle:'short'}).format(fecha);
}
async function cargarSeguimiento(){
  if(!state.grado){
    mostrarProgreso({});mostrarHistorial([]);poner('analisis-mensaje','Configura tu grado y completa una actividad para iniciar el seguimiento.');
    return;
  }
  poner('analisis-mensaje','');$('resultado-analisis').hidden=true;
  try{
    const [progreso,historial]=await Promise.all([
      pedir(`/api/perfiles/${encodeURIComponent(state.perfilId)}/progreso`),
      pedir(`/api/perfiles/${encodeURIComponent(state.perfilId)}/historial?limite=50`)
    ]);
    mostrarProgreso(progreso);mostrarHistorial(historial.actividades);
  }catch(error){
    poner('analisis-mensaje',error.mensaje||'No se pudo cargar tu historial. Revisa la conexión y la migración de MySQL.');
  }
}
async function analizarHistorial(){
  if(!state.grado){ir('perfil');poner('perfil-mensaje','Registra tu grado antes de analizar tu progreso.');return;}
  const boton=$('analizar-historial');boton.disabled=true;poner('analisis-mensaje','TutorLoreto AI está revisando tus actividades…');$('resultado-analisis').hidden=true;
  try{
    const datos=await pedir(`/api/perfiles/${encodeURIComponent(state.perfilId)}/analisis`,{method:'POST'});
    poner('orientacion-ia',datos.orientacion);$('resultado-analisis').hidden=false;
    poner('analisis-mensaje',`Se revisaron ${datos.actividades_analizadas} actividades guardadas.`);
  }catch(error){poner('analisis-mensaje',error.mensaje||'No se pudo analizar el historial. Comprueba que Ollama esté disponible.');}
  finally{boton.disabled=false;}
}
document.addEventListener('click',evento=>{
  const desactivar=evento.target.closest('[data-desactivar-cuenta]');
  if(desactivar){desactivarCuenta(desactivar.dataset.desactivarCuenta);return;}
  const tema=evento.target.closest('[data-practicar]');
  if(tema){state.temaPendiente=tema.dataset.practicar||'';state.asignaturaPendiente=Number(tema.dataset.asignatura)||null;ir('practica');return;}
  const boton=evento.target.closest('[data-ir]');if(boton)ir(boton.dataset.ir);
});
$('form-login').addEventListener('submit',autenticar);
$('form-cambiar-contrasena').addEventListener('submit',guardarContrasena);
$('form-cuenta-escolar').addEventListener('submit',crearCuentaEscolar);
$('cuenta-rol').addEventListener('change',actualizarFormularioCuenta);
$('actualizar-cuentas').addEventListener('click',cargarCuentas);
$('cuentas-cambiar-contrasena').addEventListener('click',()=>ir('cambiar_contrasena'));
$('cuentas-cerrar-sesion').addEventListener('click',cerrarSesion);
$('contrasena-cerrar-sesion').addEventListener('click',cerrarSesion);
$('inicio-cambiar-contrasena').addEventListener('click',()=>ir('cambiar_contrasena'));
$('inicio-cerrar-sesion').addEventListener('click',cerrarSesion);
$('buscar-asignatura').addEventListener('input',()=>{if(state.vista==='asignaturas')mostrarAsignaturas();});
$('biblioteca-buscar-curso').addEventListener('input',()=>{if(state.vista==='biblioteca'&&!$('biblioteca-cursos').hidden)mostrarBibliotecaCursos();});
$('biblioteca-buscar-tema').addEventListener('input',()=>{if(state.vista==='biblioteca'&&!$('biblioteca-temas').hidden)mostrarBibliotecaTemas();});
$('biblioteca-filtro-grado').addEventListener('change',evento=>{state.bibliotecaGradoFiltro=evento.currentTarget.value;if(state.vista==='biblioteca'&&!$('biblioteca-temas').hidden)mostrarBibliotecaTemas();});
$('biblioteca-volver-cursos').addEventListener('click',mostrarBibliotecaCursos);
$('biblioteca-volver-temas').addEventListener('click',mostrarBibliotecaTemas);
$('biblioteca-practicar-tema').addEventListener('click',()=>practicarTemaBiblioteca());
$('form-biblioteca-respuesta').addEventListener('submit',enviarPracticaBiblioteca);
$('biblioteca-practica-libre').addEventListener('click',()=>{
  const materia=state.asignaturas.find(item=>item.id===state.bibliotecaCursoId);
  if(!materia)return;
  state.temaPendiente=`Tema de ${materia.nombre}`;state.asignaturaPendiente=materia.id;ir('practica');
});
$('form-perfil').addEventListener('submit',guardarPerfil);
$('form-practica').addEventListener('submit',crearPractica);
$('form-respuesta-practica').addEventListener('submit',revisarPractica);
$('otra-practica').addEventListener('click',nuevaPractica);
$('actualizar-progreso').addEventListener('click',cargarSeguimiento);
$('analizar-historial').addEventListener('click',analizarHistorial);
$('pregunta').addEventListener('input',()=>{state.pregunta=$('pregunta').value;actualizarContador();});
$('continuar-asignatura').addEventListener('click',()=>{if(state.seleccionada!==null)ir('consulta');});
$('enviar').addEventListener('click',guardarConsulta);
$('generar-explicacion').addEventListener('click',generarExplicacion);
$('reintentar-ia').addEventListener('click',generarExplicacion);
$('otra-consulta').addEventListener('click',nuevaPregunta);
$('otra-consulta-registro').addEventListener('click',nuevaPregunta);
$('comprobar-conexion').addEventListener('click',comprobarConexion);
$('reintentar-red').addEventListener('click',async()=>{try{await pedir('/api/estado');await cargarAsignaturas();ir('inicio');}catch{decir('El servidor todavía no responde.');}});
$('reintentar-asignaturas').addEventListener('click',cargarAsignaturas);
$('limpiar-busqueda').addEventListener('click',()=>{$('buscar-asignatura').value='';ir('asignaturas');});

/* Ocultar resultados anteriores cuando cambian los datos */
$('form-desempeno').addEventListener('input', () => {
  $('des-mensaje').textContent = '';
  $('des-resultado').hidden = true;
});

/* Pantalla 15: análisis predictivo local - PoC S9 */
$('form-desempeno').addEventListener('submit', async (evento) => {
  evento.preventDefault();

  const formulario = evento.currentTarget;
  const boton = formulario.querySelector('button[type="submit"]');
  const mensaje = $('des-mensaje');
  const resultado = $('des-resultado');

  const datos = Object.fromEntries(
    [...new FormData(formulario)].map(([clave, valor]) => [
      clave, Number(valor)
    ])
  );

  boton.disabled = true;
  mensaje.textContent = 'Analizando tus resultados...';
  resultado.hidden = true;

  try {
    const respuesta = await pedir('/api/prediccion/refuerzo', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(datos)
    });

    $('des-clasificacion').textContent = respuesta.resultado;
    $('des-recomendacion').textContent = respuesta.recomendacion;
    resultado.hidden = false;
    mensaje.textContent = 'Análisis completado.';
  } catch (error) {
    mensaje.textContent = error.mensaje || 'No se pudo analizar el desempeño.';
  } finally {
    boton.disabled = false;
  }
});

window.addEventListener('popstate',()=>ir(location.hash.slice(1),{historial:false}));
window.addEventListener('hashchange',()=>{if(location.hash.slice(1)!==state.vista)ir(location.hash.slice(1),{historial:false});});
comprobarSesion();

import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
const source=readFileSync(new URL('../app.js',import.meta.url),'utf8');
const fn=source.slice(source.indexOf('function safeEmbedUrl('),source.indexOf('function openVideo('));
const context=vm.createContext({URL});vm.runInContext(fn,context);
test('static player accepts exact Vimeo ID and strips unknown query parameters',()=>{
  assert.equal(context.safeEmbedUrl({id:'vimeo-123',embed_url:'https://player.vimeo.com/video/123?h=fakehash&tracking=unused'}),'https://player.vimeo.com/video/123?h=fakehash&dnt=1');
});
test('static player rejects foreign hosts, credentials, mismatched IDs and invalid hashes',()=>{
  for(const embed_url of ['javascript:alert(1)','https://evil.test/video/123','https://player.vimeo.com/video/456','https://user@player.vimeo.com/video/123','https://player.vimeo.com/video/123?h=','https://player.vimeo.com/video/123?h=one&h=two'])
    assert.equal(context.safeEmbedUrl({id:'vimeo-123',embed_url}),'');
});
test('frontend requires no member service endpoints',()=>{
  assert.doesNotMatch(source,/\/api\/(session|playback)|memberAccess|checkMembership/);
});

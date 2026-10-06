# Video analizi ve Python PoC karşılığı

Kaynak: [16. Error Handling and Building Fault Tolerant Systems](https://www.youtube.com/watch?v=8NaM_9aKS24).

İnceleme, videonun tamamına ait İngilizce otomatik altyazı dökümü üzerinden yapıldı. Görsel ekran anlatımını bağımsız olarak doğrulamadım; otomatik dökümde sözcük hataları olabilir. Aşağıdaki zamanlar yaklaşık bölüm başlangıçlarıdır. Video analiz servisi başarısız oldu; alternatif altyazı erişimi başarılı oldu.

## Videonun ana fikri

Hata yönetimi yalnızca `try/except` değildir. Hataları beklemek, erken tespit etmek, etkilerini sınırlamak ve kullanıcıya anlaşılır bir yanıt üretmek gerekir. Global error handler bu yaklaşımın HTTP sınırındaki son katmanıdır. Konuşmacı başta bunun framework veya kod odaklı bir ders olmadığını, bir mühendislik yaklaşımı anlattığını belirtiyor.

| Zaman | Konu | Bizim çalışmaya etkisi |
|---|---|---|
| [02:00](https://www.youtube.com/watch?v=8NaM_9aKS24&t=120s) | Mantık hataları: kod çalışır ama sonuç yanlıştır | Exception oluşmazsa global handler bunu keşfedemez; iş kuralı testleri gerekir. |
| [05:26](https://www.youtube.com/watch?v=8NaM_9aKS24&t=326s) | Veritabanı bağlantısı, constraint, sorgu ve deadlock hataları | Her veritabanı hatasının HTTP anlamı aynı değildir. |
| [10:42](https://www.youtube.com/watch?v=8NaM_9aKS24&t=642s) | Dış servis, ağ, rate limit ve kesinti | Retry/fallback, HTTP hata biçimlendirmesinden ayrı tasarlanır. |
| [17:24](https://www.youtube.com/watch?v=8NaM_9aKS24&t=1044s) | Girdi doğrulama | PoC'de miktar 0 isteği servise ulaşmadan 422 olur. |
| [20:10](https://www.youtube.com/watch?v=8NaM_9aKS24&t=1210s) | Configuration ve erken başarısız olma | Eksik zorunlu ayar başlangıçta kontrol edilir; request handler başlangıç hatalarının çözümü değildir. |
| [24:13](https://www.youtube.com/watch?v=8NaM_9aKS24&t=1453s) | Önleme, health check | Sadece sunucunun ayakta olması işlevin doğru olduğunu kanıtlamaz. |
| [29:37](https://www.youtube.com/watch?v=8NaM_9aKS24&t=1777s) | Monitoring ve observability | Hata oranı yanında gecikme ve iş metrikleri de izlenir. |
| [33:25](https://www.youtube.com/watch?v=8NaM_9aKS24&t=2005s) | Recovery, retry, etkiyi sınırlama | Global handler otomatik iyileşme mekanizması değildir. |
| [39:08](https://www.youtube.com/watch?v=8NaM_9aKS24&t=2348s) | Hatanın bağlamla üst katmana taşınması | Python'da `raise` ve gerektiğinde `raise ... from exc`. |
| [41:42](https://www.youtube.com/watch?v=8NaM_9aKS24&t=2502s) | Global error handling | Bu PoC'nin asıl odağı. |
| [60:09](https://www.youtube.com/watch?v=8NaM_9aKS24&t=3609s) | Güvenli mesajlar ve loglar | Teknik ayrıntı yanıta konmaz; hassas veri loglaması ayrıca yönetilir. |

## Global error handling bölümünün açıklaması

Konuşmacı routing → handler → service → repository yapısını kullanıyor. Kitap oluşturma örneğinde isim uzunluğu doğrulamada hata verebilir; aynı isimle kayıt veritabanında unique constraint hatası verebilir. Bu hatalar üst katmana taşınır ve merkezi katman hata türüne göre yanıt üretir. Kitap aramasında bulunamayan kaynak için 404 örneği de veriliyor. Kazançları tutarlı yanıtlar ve tekrar eden hata işleme kodunun azalması.

Bizdeki karşılığı:

```text
GET /products/999
  → main.py: product(999)
  → domain.py: get_product(999)
  → repository.py: find_product(999) → None
  → domain.py: raise ProductNotFound(...)
  → errors.py: domain_handler(...)
  → HTTP 404 + ortak JSON + X-Request-ID
```

Repository veri erişimini yapar. Service/domain katmanı “ürün bulunamadı” anlamını üretir. HTTP handler bu anlama HTTP karşılığı verir. Hata oluşunca o fonksiyonun normal akışı kesilir; handler'ın yanıt üretmesi işlemin başarılı olduğu anlamına gelmez.

Bir diğer deney:

```text
POST /orders/preview {"product_id": 1, "quantity": 4}
  → girdi doğrulaması başarılı
  → servis ürünü bulur, stok 3
  → raise InsufficientStock
  → merkezi handler
  → HTTP 409 / INSUFFICIENT_STOCK
```

## Videoyu Python'a aktarırken yaptığımız seçimler

1. **Middleware yerine FastAPI exception handler kayıtları:** Aynı merkezi yaklaşımı framework'ün mekanizmasıyla uygularız. Middleware burada request kimliği ekler; hata sınıflandırması `app.exception_handler` kayıtlarındadır.
2. **400 yerine bazı durumlarda 422/409:** Video validation ve unique constraint için 400 örneği verir. Biz FastAPI'nin doğrulama geleneğini koruyarak 422, stok çatışmasına 409 kullanıyoruz. Bunlar bu API'nin bilinçli sözleşme seçimleridir.
3. **Boş sorgu sonucu otomatik exception değildir:** Videodaki “no rows” davranışı sürücüye/metoda bağlıdır. Python'da pek çok erişim metodu `None` veya boş liste döndürür. Bu nedenle repository'nin `None` sonucunu serviste `ProductNotFound` yapıyoruz. Boş bir listeleme sonucunu ise otomatik 404 yapmak gerekmez.
4. **Ham veritabanı hatasını kullanıcıya gönderme:** Gerçek DB eklenirse yalnızca tanınan constraint/driver hatalarını anlamlı uygulama exception'larına çevir; tüm `IntegrityError` türlerini aynı kullanıcı hatası sanma. Sorgu öncesi kontrol eşzamanlı istek yarışlarını engellemez; DB constraint'i yine gereklidir.
5. **Global kapsamın sınırı vardır:** HTTP isteği sırasında oluşan ve yanıt gönderilmeden yakalanan hataları yönetiyoruz. Mantık hataları, worker işleri, başlangıç hataları ve yanıt başladıktan sonraki hatalar ayrı ele alınır. “Global” bütün süreçteki tüm arızaları çözdüğü anlamına gelmez.
6. **Retry sınırlı olmalı:** Video exponential backoff anlatıyor. Gerçek uygulamada azami deneme/süre, jitter ve işlemin tekrar edilebilirliği düşünülmeli; özellikle ödeme gibi işlemler körlemesine tekrar edilmemeli. Bu PoC retry yapmaz.

## Öğrenme kontrolü

- Miktar 0 ile miktar 4 neden farklı hata? İlki giriş kısıtını, ikincisi mevcut stok kuralını ihlal eder.
- `/products/999` ve `/missing` neden aynı HTTP kodunda farklı `code` taşır? Birinde iş kaynağı yoktur, diğerinde route yoktur.
- `RuntimeError` mesajını JSON'a koyarsan ne olur? İç sistem ayrıntısını istemciye sızdırabilirsin.
- Handler exception'ı yanıta çevirince stok işlemi geri alınır mı? Hayır; transaction/rollback ayrı sorumluluktur.
- Hatalı indirim hesabı 200 döndürüyorsa global handler yakalar mı? Exception yoksa hayır; test ve iş metriği gerekir.

PoC gerçek DB constraint, circuit breaker, retry veya monitoring altyapısı içermez; bunlar videonun daha geniş fault-tolerance kapsamıdır. Burada merkezi HTTP hata yönetimini küçük ve tekrar edilebilir bir deneyle izole ettik.

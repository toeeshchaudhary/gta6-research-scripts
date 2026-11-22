p = 'work/draw/tool/Core/RageModelDecoder.cs'
s = open(p, encoding='utf-8').read()
s = s.replace('''        catch (Exception ex) when (ex is InvalidDataException or ArgumentException or OverflowException or IndexOutOfRangeException)
        { return null; }
    }''',
'''        catch (Exception ex) when (ex is InvalidDataException or ArgumentException or OverflowException or IndexOutOfRangeException)
        { LastError = ex.GetType().Name + ": " + ex.Message; return null; }
    }

    public static string LastError = "";''')
open(p, 'w', encoding='utf-8').write(s)

p2 = 'work/draw/tool/ExtractModels/Program.cs'
t = open(p2, encoding='utf-8').read()
t = t.replace('''            catch (Exception ex) { decodeError = ex.GetType().Name + ": " + ex.Message; }''',
              '''            catch (Exception ex) { decodeError = ex.GetType().Name + ": " + ex.Message; }
            if (model is null) decodeError += " | " + RageModelDecoder.LastError;''')
open(p2, 'w', encoding='utf-8').write(t)
print('patched last error')

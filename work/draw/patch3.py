p=r'work/draw/tool/ExtractModels/Program.cs'
s=open(p,encoding='utf-8').read()
s=s.replace("""            RageModel? model = RageModelDecoder.Decode(decodeSystem, graphics);
            if (model is null) return Row(offset, name, hash, "fail", 0, 0, "-", "decoder rejected the drawable");""","""            RageModel? model = null;
            string decodeError = "";
            try { model = RageModelDecoder.Decode(decodeSystem, graphics); }
            catch (Exception ex) { decodeError = ex.GetType().Name + ": " + ex.Message; }
            if (model is null) return Row(offset, name, hash, "fail", 0, 0, "-", "decoder rejected the drawable " + decodeError);""")
open(p,'w',encoding='utf-8').write(s)
print('ok')
